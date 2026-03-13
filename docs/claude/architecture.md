# PubliSync 아키텍처 패턴 상세

> 8개 아키텍처 영역의 핵심 패턴 정리. 상세 시퀀스/다이어그램은 `docs/시스템_아키텍처_설계서.md` 참조.

---

## 1. 멀티테넌트

### 격리 전략

**논리적 격리** (Shared Database, Shared Schema) — PostgreSQL RLS 기반.

### RLS 정책 SQL

```sql
-- 모든 테넌트 격리 대상 테이블에 공통 적용
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;

-- 테넌트 격리 정책
CREATE POLICY tenant_isolation ON {table_name}
  USING (organization_id = current_setting('app.current_org_id')::uuid);

-- 시스템 관리자(SA) 우회 정책
CREATE POLICY sa_bypass ON {table_name}
  USING (current_setting('app.user_role', true) = 'SYSTEM_ADMIN');
```

### RLS 적용/미적용 테이블

**RLS 적용 (organization_id FK):**

| 테이블 | Phase | 테이블 | Phase |
|---|---|---|---|
| contents | 1-A | notifications | 1-B |
| comments | 1-B | audit_logs | 1-B |
| channels | 1-A | media_assets | 2 |
| approvals | 1-A | reports | 3 |
| calendar_events | 2 | | |

**RLS 미적용 (전역 데이터):**

| 테이블 | 근거 |
|---|---|
| users | 여러 기관에 소속 가능 (다대다) |
| organizations | 기관 목록은 전역 조회 필요 |
| roles | 역할 정의는 시스템 전역 |
| system_announcements | 시스템 공지 |

### Workspace 미들웨어 흐름

```
요청 수신
  → X-Workspace-Id 헤더에서 org_id 추출
  → 사용자의 해당 기관 소속 여부 확인
  → DB 세션에 세션 변수 설정:
    SET LOCAL app.current_org_id = '{org_id}'
    SET LOCAL app.user_role = '{user.role}'
  → 이후 모든 SELECT/INSERT/UPDATE/DELETE에 RLS 자동 적용
  → 트랜잭션 종료 시 SET LOCAL 자동 리셋
```

### 7계층 격리 키 패턴

| 계층 | 격리 방식 | 예시 |
|---|---|---|
| **Database** | RLS 정책 | `organization_id = current_setting(...)` |
| **API** | X-Workspace-Id 헤더 | 미들웨어에서 추출 → 세션 변수 설정 |
| **파일** | org_id 프리픽스 | `publisync-media/{org_id}/uploads/...` |
| **캐시** | 키에 org_id 포함 | `cache:dashboard:{org_id}:summary` |
| **비동기** | Celery 작업 인자 | `task.delay(content_id, org_id=org_id)` |
| **SSE** | 채널명에 org_id | `sse:channel:{org_id}:{user_id}` |
| **검색** | 테넌트 필터 | `filter: organization_id = {org_id}` [Phase 2] |

---

## 2. 인증/인가

### JWT 구조

- **알고리즘:** HS256 (대칭키)
- **Access Token TTL:** 30분
- **Refresh Token TTL:** 7일 (rememberMe 옵션 시 30일)
- **블랙리스트:** Redis (`jwt:blacklist:{jti}`, TTL = access_token TTL)
- **비밀번호:** passlib + bcrypt 12 라운드
- **비밀번호 재설정 토큰 TTL:** 24시간
- **초대 토큰 TTL:** 7일

### 토큰 갱신 흐름

```
1. API 호출 → 401 Unauthorized
2. refreshToken으로 POST /auth/refresh
3. 성공 → 새 accessToken 저장 → 원본 요청 재시도
4. 실패 → 로그아웃 → /login 리다이렉트
5. 동시 요청 경쟁 방지: 갱신 중인 Promise 공유
```

### 5회 잠금 정책

- 연속 5회 로그인 실패 → 계정 잠금 30분
- 잠금 상태에서 로그인 시도 → 423 Locked 반환
- Redis 카운터로 추적: `login:fail:{user_id}`

### RBAC 매트릭스

| 리소스\역할 | SA | AM | AO | CD |
|---|:---:|:---:|:---:|:---:|
| 콘텐츠 작성 | - | ✅ | ✅ | - |
| 콘텐츠 게시 | - | ✅ | - | - |
| 콘텐츠 승인 | - | - | - | ✅ |
| 채널 연동 | - | ✅ | - | - |
| 사용자 관리 | ✅ | ✅ | - | - |
| 시스템 관리 | ✅ | - | - | - |
| 대시보드 조회 | ✅ | ✅ | ✅ | ✅ |
| 댓글 관리 | - | ✅ | ✅ | - |
| 감사 로그 | - | ✅ | - | ✅ |
| 워크플로우 설정 | - | ✅ | - | - |

---

## 3. 실시간 통신

### SSE + Redis Pub/Sub 흐름

```
Browser EventSource    →  Nginx (proxy_buffering off)
  → API Server (sse-starlette)  →  Redis SUBSCRIBE sse:channel:{org_id}:{user_id}

이벤트 발생 (Celery Worker 등):
  → Redis PUBLISH sse:channel:{org_id}:{user_id}  →  API Server  →  SSE 전송  →  Browser
```

**Nginx SSE 설정 핵심:**
- `proxy_buffering off` — 즉시 전달
- `proxy_read_timeout 86400s` — 24시간 연결 유지
- `chunked_transfer_encoding off`

**재연결:** EventSource 기본 자동 재연결, `Last-Event-ID`로 미수신 이벤트 재전송, 5회 연속 실패 → 폴링 Fallback

### 알림 채널 계층 (4개)

| 채널 | 지연 | 도달 보장 | Phase |
|---|---|---|---|
| **SSE** | < 1초 | 접속 중만 | 1-A |
| **Web Push** (pywebpush) | 1~5초 | SW 등록 시 | 1-B |
| **텔레그램 Bot** | 1~3초 | 앱 설치 시 | 1-B |
| **이메일** (FastAPI-Mail) | 수초~수분 | 이메일 주소만 | 1-A |

### 알림 유형 × 채널 매핑

| 알림 유형 | SSE | Web Push | 텔레그램 | 이메일 |
|---|:---:|:---:|:---:|:---:|
| 승인 요청/결과 | ✅ | ✅ | 요청만 | - |
| 위험 댓글 | ✅ | ✅ | ✅ | - |
| 게시 완료 | ✅ | - | - | - |
| 게시 실패 | ✅ | ✅ | ✅ | - |
| 토큰 만료 임박 | ✅ | ✅ | ✅ | ✅ |
| 사용자 초대 | - | - | - | ✅ |
| 비밀번호 재설정 | - | - | - | ✅ |
| AI 작업 완료 | ✅ | - | - | - |

### 이메일 파이프라인

```
API Server / Celery Beat  →  Celery (system 큐)  →  FastAPI-Mail + Jinja2 템플릿  →  SMTP
```

**템플릿:** invite.html, reset.html, token.html, report.html, system.html
**규칙:** 모든 이메일은 Celery 경유, 재시도 3회 (1분→5분→15분), 분당 50통 Rate Limit

### 폴링 Fallback (SSE 불가 시)

```typescript
// TanStack Query 기반
useQuery(['notifications', 'unread-count'], { refetchInterval: 15_000 })  // 15초
useQuery(['dashboard', 'badge-counts'], { refetchInterval: 30_000 })      // 30초
```

---

## 4. AI 통합

### litellm 설정

```
model_list:
  기본: "gpt-4o-mini"              ← 비용 효율 (일반 텍스트)
  고품질: "gpt-4o"                  ← 복잡한 분석 (리포트, 여론 예측)
  Fallback 1: "claude-sonnet-4-6"  ← OpenAI 장애 시
  Fallback 2: "gemini-1.5-flash"   ← 전체 장애 시 최후 수단

fallbacks: OpenAI → Anthropic → Google → Fallback 메시지
재시도: num_retries=2, timeout=10(동기)/60(비동기)
```

### 동기/비동기 분기 (10초 기준)

| 동기 (< 10초, 200 OK) | 비동기 (>= 10초, 202 Accepted + jobId) |
|---|---|
| 제목/설명/해시태그 생성 (F02) | 자막 생성 STT (F03) |
| 답글 초안 (F05) | 리포트 생성 (F19) |
| 톤앤매너 변환 (F17) | 숏폼 추출 (F15) |
| 표현 검수 (F21) | 감성 분석 배치 (F04) |
| 번역 (F22) | 영상 처리 (F03) |
| | 썸네일 생성 (F16) |

**비동기 진행 추적:** `GET /ai/jobs/:jobId` 폴링 (3초) 또는 SSE 이벤트

### 기능별 모델 라우팅

| 기능 | 모델 | 근거 |
|---|---|---|
| 제목/설명/해시태그 (F02) | gpt-4o-mini | 짧은 텍스트, 비용 효율 |
| 감성 분석 (F04) | gpt-4o-mini | 분류 작업 |
| 답글 초안 (F05) | gpt-4o-mini | 짧은 텍스트 |
| 톤앤매너 변환 (F17) | gpt-4o-mini | 텍스트 변환 |
| 표현 가이드 검수 (F21) | gpt-4o | 높은 정확도 필요 |
| 자막 생성 (F03) | Whisper API | 전용 STT |
| 리포트 생성 (F19) | gpt-4o | 장문 분석 |
| 여론 예측 (F18) | gpt-4o | 복잡한 추론 |
| 번역 (F22) | gpt-4o-mini | 비용 효율 |
| 썸네일 분석 (F16) | gpt-4o (vision) | 이미지 분석 |

### Human-in-the-Loop 공통 응답

```json
{
  "isAiGenerated": true,
  "confidence": 0.85,
  "fallbackAvailable": true,
  "model": "gpt-4o-mini",
  "suggestions": [{ "content": "...", "score": 0.85 }],
  "usage": { "promptTokens": 150, "completionTokens": 50, "estimatedCost": 0.0003 }
}
```

### Fallback 매트릭스

| 기능 | 타임아웃/장애 시 | 품질 미달 시 |
|---|---|---|
| 제목/설명/해시태그 | "직접 입력하세요" 안내 | 사용자가 수정 후 사용 |
| 감성 분석 | 라벨 미부여, 수동 분류 대기 | "미분류" 표시, 수동 태깅 |
| 답글 초안 | "직접 작성하세요" + 템플릿 제안 | 사용자가 수정 후 게시 |
| 톤앤매너 변환 | 원문 그대로 유지 | 사용자가 수동 수정 |
| 표현 검수 | "AI 검수 불가, 수동 검수" 안내 | 검수자 수동 확인 |
| 자막 생성 | "자막 생성 실패" + 수동 입력 UI | 자막 편집기에서 수정 |
| 리포트 생성 | "실패, 재시도" 안내 | 사용자가 텍스트 수정 |
| 숏폼 추출 | "수동 구간 지정" UI | 사용자가 구간 조정 |

**핵심 원칙:** AI 장애가 게시, 댓글 관리, 승인 등 핵심 업무를 중단시키지 않는다.

### 비용 관리

- `ai_usage_logs` 테이블: organization_id, feature, model, tokens, cost, created_at
- 기관별 월간 AI 호출 한도 설정 가능
- 80% 도달 → 관리자 알림, 100% → AI 비활성화 + Fallback
- litellm `usage` 필드 자동 파싱

---

## 5. 비동기 처리 (Celery)

### 3개 큐

| 큐 | 작업 유형 | 분리 근거 |
|---|---|---|
| `publish` | 콘텐츠 게시, 재시도 | 시간 민감 (예약 게시), AI 지연에 영향 X |
| `ai` | AI 생성, 감성 분석, 자막, 리포트 | 응답 10~60초, 비용 발생, 독립 관리 |
| `system` | 댓글 수집, 토큰 갱신, 알림, 동기화 | 주기적 배치, 다른 큐 영향 X |

> Phase 1-A에서는 단일 큐(default), Phase 1-B에서 3분할

### 재시도 전략

| 작업 유형 | 최대 재시도 | 백오프 | 타임아웃 | 실패 시 |
|---|:---:|---|:---:|---|
| 콘텐츠 게시 | 3 | 지수 (5m→15m→30m) | 120초 | 알림, 수동 재시도 안내 |
| AI 메타데이터 | 2 | 고정 (10초) | 30초 | Fallback 메시지 |
| 감성 분석 | 2 | 고정 (5초) | 20초 | 수동 분류 대기 |
| 댓글 수집 | 3 | 지수 (1m→5m→15m) | 60초 | 다음 주기 재시도 |
| 토큰 갱신 | 3 | 지수 (5m→30m→2h) | 30초 | EXPIRED 상태, 알림 |
| 알림 발송 | 2 | 고정 (30초) | 15초 | 실패 로그 기록 |
| 리포트 생성 | 1 | — | 300초 | 실패 알림 |
| 영상 처리 | 1 | — | 600초 | 실패 알림 |

### 우선순위

```
P1 (긴급)  : 긴급 게시 (Fast Track), 위험 댓글 알림
P2 (높음)  : 예약 게시 (시간 도달), 승인 결과 알림
P3 (보통)  : AI 메타데이터, 감성 분석, 일반 알림
P4 (낮음)  : 댓글 정기 수집, 토큰 갱신, 데이터 동기화
P5 (배경)  : 리포트 생성, 영상 처리, 벤치마크 수집
```

### Celery Beat 스케줄

| 작업 | 큐 | 주기 | Phase |
|---|---|---|---|
| 예약 게시 확인 | publish | 1분 | 1-A |
| 대시보드 캐시 갱신 | system | 5분 | 1-A |
| 사이드바 뱃지 갱신 | system | 30초 | 1-A |
| 토큰 갱신 확인 | system | 1시간 | 1-A |
| 만료 세션 정리 | system | 6시간 | 1-A |
| 댓글 수집 | system | 5분 | 1-B |
| 감성 분석 배치 | ai | 10분 | 1-B |
| 플랫폼 데이터 동기화 | system | 1시간 | 1-B |
| 감사 로그 파티션 관리 | system | 매월 1일 | 1-B |
| 스토리지 용량 체크 | system | 일 1회 | 2 |

### 워커 설정

```bash
celery -A app.core.celery_app worker -Q publish,ai,system --max-tasks-per-child=100 --concurrency=4
```

- `--max-tasks-per-child=100` — 메모리 누수 방지 (100개 작업 후 프로세스 재시작)
- Flower (Phase 1-B) — 실시간 워커/큐/작업 모니터링

---

## 6. 플랫폼 연동

### PlatformAdapter 인터페이스

```python
class PlatformAdapter(ABC):
    async def publish(content) -> PublishResult
    async def get_comments(channel) -> list[Comment]
    async def reply_comment(id, text) -> Result
    async def hide_comment(id) -> Result
    async def delete_comment(id) -> Result
    async def get_analytics(period) -> Analytics
    async def refresh_token(channel) -> Token
    async def get_channel_info() -> ChannelInfo
    async def validate_content(content) -> list[Error]
```

**팩토리 패턴:** `adapter = get_adapter(channel.platform)`

### 5개 플랫폼 기능 매트릭스

| 메서드 | YouTube | Instagram | Facebook | X | 네이버 블로그 |
|---|:---:|:---:|:---:|:---:|:---:|
| publish | ✅ | ✅ | ✅ | ✅ | ✅ |
| get_comments | ✅ | ✅ | ✅ | ✅ | ❓ (PoC) |
| reply_comment | ✅ | ✅ | ✅ | ✅ | ❌ |
| hide_comment | ✅ | ❌ | ✅ | ❌ | ❌ |
| delete_comment | ✅ | ✅ | ✅ | ✅ | ❌ |
| get_analytics | ✅ | ✅ | ✅ | ✅ | 제한적 |

> 미지원 메서드 → `PlatformNotSupportedError`, FE에서 버튼 비활성화

### Rate Limit 중앙 관리

```
Redis 카운터: ratelimit:{platform}:{org_id}:{window}
  → 쿼터 충분: 호출 허용
  → 80% 도달: 속도 조절 (백프레셔, 간격 1초→5초)
  → 90% 도달: 낮은 우선순위 요청 큐잉
  → 100% 도달: 모든 요청 큐잉, 윈도우 리셋 대기
```

**플랫폼별 Rate Limit:**

| 플랫폼 | 주요 제한 | 윈도우 |
|---|---|---|
| YouTube Data API | 10,000 단위/일 | 24h |
| Instagram Graph API | 200 호출/시간 | 1h |
| Facebook Graph API | 200 호출/시간/사용자 | 1h |
| X API v2 | 300 트윗/3시간 (Basic) | 3h |
| 네이버 블로그 API | 일 제한 있음 | 24h |

### 토큰 상태 머신

```
DISCONNECTED  →(OAuth 완료)→  ACTIVE  →(expires_at - 1h)→  EXPIRING
                                  ↑                            │
                                  │                     ┌──────┴──────┐
                                  │                  갱신 성공      갱신 실패
                                  │                     │              │
                                  └─────────────────────┘        EXPIRED
                                                                    │
                                                              (재연동 OAuth)
                                                                    │
                                                                 ACTIVE
```

---

## 7. 파일 처리

### MinIO 업로드 흐름

**소용량 (< 50MB):**
```
Browser → POST /media/upload (multipart) → API Server → PUT MinIO → 201 { mediaId, url }
```

**대용량 (>= 50MB):**
```
Browser → POST /media/upload/initiate → API Server → Presigned URL 발급
Browser → PUT presignedUrl (직접 MinIO 업로드)
Browser → POST /media/upload/complete → API Server → DB 메타 기록 → 201 { mediaId, url }
```

### 버킷 구조

```
publisync-media/
├── {org_id}/                  ← 기관별 격리 (1-depth)
│   ├── uploads/{year}/{month}/{uuid}.*   ← 원본 미디어
│   ├── thumbnails/{content_id}_thumb.jpg ← 썸네일
│   ├── shortforms/            ← AI 숏폼 [Phase 2]
│   ├── reports/{report_id}.pdf ← 리포트 [Phase 3]
│   └── profiles/{user_id}.jpg ← 프로필
└── system/
    ├── templates/             ← 이메일 에셋
    └── defaults/              ← 기본 아바타, 로고
```

### Presigned URL

| 용도 | 메서드 | TTL | 경로 제약 |
|---|---|:---:|---|
| 업로드 | PUT | 1시간 | `{org_id}/uploads/{year}/{month}/{uuid}.*` |
| 다운로드 | GET | 4시간 | `{org_id}/**` (해당 기관만) |
| 썸네일 | GET | 24시간 | `{org_id}/thumbnails/*` |

### 삭제 정책

- 소프트 삭제: `is_deleted = true` (즉시)
- 물리 삭제: Celery 배치 30일 후 MinIO 실제 삭제
- 감사 로그: 삭제 요청자, 사유, 일시 기록

### 스토리지 할당량

- 기본 할당: **50GB/기관**
- 80% → 관리자 경고 알림, 95% → 업로드 제한 + 긴급 알림
- 6개월 미접근 파일 → 아카이브 버킷 이동 [Phase 2+]

### 파일 검증 (클라이언트)

- 이미지: 10MB, 영상: 2GB
- MIME 타입 확인
- 파일 수 제한: 10개

### StorageBackend 추상화 (v2.0 추가)

```
app/integrations/storage/
├── base.py           ← StorageBackend ABC (7 메서드)
├── local.py          ← LocalStorageBackend (개발용, ./uploads/)
├── minio_backend.py  ← MinIOStorageBackend (프로덕션, S3 호환)
├── routes.py         ← 로컬 파일 서빙 엔드포인트 (/api/v1/storage/files/*)
└── __init__.py       ← get_storage() 팩토리 (@lru_cache 싱글턴) + 레거시 래퍼
```

- `STORAGE_BACKEND=local` → 로컬 파일시스템, MinIO 없이 개발 가능
- `STORAGE_BACKEND=minio` → 기존 MinIO/S3 동작
- 기존 `upload_file_to_storage()`, `get_object_stream()` 등은 `get_storage()` 위임 래퍼로 유지

### Variant 기반 게시 흐름 (v2.0 추가)

```
게시 실행 시:
├── content.variants 존재 → variant별 순회
│   ├── variant.title/body 오버라이드 적용
│   ├── variant_media → 미디어 첨부
│   ├── PlatformAdapter.publish() → PublishResult(variant_id 기록)
│   └── 전체 variant 완료 → 최종 상태 결정
│
└── content.variants 미존재 → 레거시 (channel_ids 순회, 공통 title/body)

uniform_publish=true 시 자동 변환:
├── 프론트엔드에서 channel_ids[] 전송
├── 백엔드가 각 채널별 variant 자동 생성 (title/body=null → 공통 값)
└── variant 기반 게시 실행

승인 RBAC 분기:
├── org.require_cd_review=true → AO→CD 검토→AM 승인→게시
└── org.require_cd_review=false → AO→AM 승인→게시 (기본)
```

---

## 8. 보안

### 8계층 Defense in Depth

| # | 계층 | 핵심 기술 |
|---|---|---|
| ① | 네트워크 | Docker 네트워크 격리, 외부 노출 80/443만, Nginx 유일 진입점 |
| ② | 전송 | TLS 1.3 (Nginx 종료), HSTS, HTTP→HTTPS 강제, Redis TLS |
| ③ | 인증 | JWT HS256 30분, Redis 블랙리스트, 5회 잠금, bcrypt 12r |
| ④ | 인가 | RBAC 4역할, PostgreSQL RLS (org_id), 교차 테넌트 차단 |
| ⑤ | 데이터 | Fernet 대칭 암호화 (OAuth 토큰), LUKS 볼륨, MinIO SSE-S3 |
| ⑥ | 애플리케이션 | Pydantic 입력 검증, SQLAlchemy ORM (SQL injection 방지), CORS, Rate Limit |
| ⑦ | 로깅 | structlog JSON + request_id, 개인정보 마스킹, Sentry 필터링 |
| ⑧ | 감사 | INSERT-ONLY, 월별 파티션, 3년 보관, CSV/PDF 내보내기 |

### 암호화 상세

| 구분 | 대상 | 방식 | 키 관리 |
|---|---|---|---|
| 전송 | 외부 통신 | TLS 1.3 (Nginx) | Let's Encrypt |
| 전송 | Redis | TLS + requirepass | 환경 변수 |
| 저장 (디스크) | PG 볼륨 | LUKS/dm-crypt | OS 키 |
| 저장 (오브젝트) | MinIO 파일 | SSE-S3 AES-256 | MinIO KES |
| 필드 | OAuth tokens | Fernet AES-128-CBC | `OAUTH_ENCRYPTION_KEY` 환경 변수 |
| 해싱 | 비밀번호 | bcrypt 12 라운드 | 솔트 자동 |

### 개인정보 마스킹

```
structlog 프로세서:
  이메일: kim@agency.co.kr → ***@***.kr
  전화번호: 010-1234-5678 → ***-****-5678
  주민등록번호: 패턴 감지 → *************

Sentry before_send:
  request.body: password, token, authorization 필드 제거
  request.headers: Authorization, Cookie 제거
```

### 감사 로그 구조

```
audit_logs:
  id, organization_id (RLS), actor_id, actor_role, action,
  resource_type, resource_id, changes (JSONB, 마스킹 적용),
  ip_address, user_agent, request_id, created_at
```

- INSERT-ONLY (UPDATE/DELETE 트리거 차단)
- 월별 파티션: `audit_logs_2026_03`, `audit_logs_2026_04`, ...
- 3년 초과 파티션 DROP (자동 삭제)

### 의존성 보안

- **Dependabot:** Python/Node.js 자동 업데이트 PR
- **pip-audit:** CI에서 Python 취약점 차단 (HIGH 이상)
- **pnpm audit:** CI에서 Node 취약점 차단 (high/critical)
- **Docker 이미지:** -slim/-alpine 사용, 주기적 리빌드
