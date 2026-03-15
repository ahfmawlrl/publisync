# PubliSync — 공공기관 소셜 미디어 통합 관리 플랫폼

> 수탁업체가 다수 위탁기관(공공기관)의 SNS 계정(YouTube, Instagram, Facebook, X, 네이버 블로그)을
> 하나의 웹 대시보드에서 통합 관리하며, AI로 반복 업무를 절감하는 멀티테넌트 SaaS.

---

## 핵심 원칙 6가지

| # | 원칙 | 설명 |
|---|---|---|
| 1 | **Human-in-the-Loop** | AI 산출물은 항상 "제안" — 최종 결정은 사람이 한다 |
| 2 | **Fallback 필수** | 모든 AI 기능에 수동 대체 경로 제공 (AI 실패 시에도 업무 가능) |
| 3 | **워크플로우 내장 AI** | AI 기능은 별도 메뉴가 아닌, 게시·댓글·리포트 작업 화면 안에서 호출 |
| 4 | **멀티테넌트 격리** | PostgreSQL RLS 기반, 위탁기관 데이터를 행 수준으로 격리 |
| 5 | **Phase 점진 투입** | 최소 MVP(1-A) → 확장 MVP(1-B) → Phase 2/3/4 순으로 라이브러리·기능 추가 |
| 6 | **공공기관 규정 준수** | KWCAG 2.2 접근성, 개인정보보호법, CSAP 지향 |

---

## 기술 스택 요약

### 프론트엔드 (22개)

| 영역 | 기술 |
|---|---|
| 코어 | React 19 · TypeScript 5 · Vite 6 · pnpm |
| 상태 | TanStack Query v5 (서버) · Zustand 5 (클라이언트 UI) |
| UI | Ant Design 5 · Tailwind CSS 4 · Lucide React |
| 라우팅·폼 | React Router v7 · React Hook Form v7 · Zod 3 |
| HTTP·유틸 | Axios (인터셉터 체인) · dayjs (날짜) |
| 차트 | Recharts (기본) · @ant-design/charts (히트맵·워드클라우드, Phase 2+) |
| 전문 UI | FullCalendar v6 (Phase 2) · Video.js 8 (Phase 2) · wavesurfer.js 7 (Phase 2) · Tiptap v2 (Phase 3) · react-dropzone · @tanstack/react-virtual (Phase 1-B) · react-i18next (Phase 4) |
| 테스트 | Vitest · React Testing Library · Playwright |
| 품질 | ESLint · Prettier · eslint-plugin-jsx-a11y |

### 백엔드 (28개)

| 영역 | 기술 |
|---|---|
| 코어 | FastAPI 0.115+ · Python 3.11 · uvicorn · SQLAlchemy 2.0 (async) · asyncpg · Alembic · Pydantic v2 |
| 인증 | python-jose (JWT HS256) · passlib (bcrypt) · Authlib (OAuth) |
| 실시간·비동기 | sse-starlette (SSE) · Celery 5 (3큐: publish/ai/system) · Redis 7 (브로커+캐시+Pub/Sub) |
| 이메일 | FastAPI-Mail · Jinja2 (HTML 템플릿) |
| AI | litellm (멀티 프로바이더 라우팅) · httpx |
| 플랫폼 | httpx · python-telegram-bot · pywebpush |
| 파일 | minio-py · Pillow (Phase 1-B+) · ffmpeg-python (Phase 2) · WeasyPrint (Phase 3, PDF 리포트) |
| 보안 | cryptography (Fernet 토큰 암호화) · slowapi (Rate Limit) |
| 로깅 | structlog (JSON + request_id + PII 마스킹) |
| 검색 | Meilisearch 1.x (Phase 2, Phase 1-A는 tsvector) |
| 테스트 | pytest · pytest-asyncio · httpx (TestClient) |
| 품질 | Ruff · mypy · pre-commit |

### 인프라 (8개)

| 영역 | 기술 |
|---|---|
| 컨테이너 | Docker Compose (dev) · Docker (prod) |
| 프록시 | Nginx 1.27 (TLS 종료 · 리버스 프록시 · SSE) |
| TLS | Let's Encrypt (certbot) |
| DB | PostgreSQL 16 (RLS · JSONB · tsvector · Partitioning) |
| 저장소 | 로컬 FS (개발) · MinIO/S3 (프로덕션) — StorageBackend 추상화 |
| CI/CD | GitHub Actions |
| 모니터링 | Sentry · Flower 2.x (Phase 1-B) · Prometheus · Grafana · Loki (Phase 3) |
| 보안 | Dependabot · pip-audit · pnpm audit |

---

## 디렉토리 구조

### 프론트엔드

```
src/
├── app/                    ← 진입점, 프로바이더, 글로벌 설정
│   ├── App.tsx             ← RouterProvider + QueryClientProvider + ConfigProvider
│   ├── router.tsx          ← 라우트 정의 (lazy import)
│   └── providers/          ← Theme, Auth, Workspace Provider
├── shared/                 ← 공유 레이어
│   ├── api/                ← Axios 인스턴스, 인터셉터, 타입
│   ├── components/         ← 범용 UI (PageHeader, StatusBadge 등)
│   ├── hooks/              ← useAuth, useWorkspace, usePermission
│   ├── layouts/            ← GlobalLayout, Sidebar, TopBar
│   ├── stores/             ← Zustand (UI 전용: sidebarCollapsed, theme, modal)
│   ├── types/              ← User, Organization, Role 등 공용 타입
│   └── utils/              ← dayjs 포맷, 권한 체크 등
├── features/               ← 기능별 모듈 (도메인 경계 일치)
│   ├── auth/               ← 로그인, 토큰 갱신, 비밀번호
│   ├── dashboard/          ← 대시보드 (F06)
│   ├── contents/           ← 콘텐츠 CRUD + Variant (F01, F09)
│   ├── approvals/          ← 승인 워크플로우 (F09)
│   ├── comments/           ← 댓글 관리 (F04, F05) [Phase 1-B]
│   ├── channels/           ← 채널 연동 (F12)
│   ├── media/              ← 미디어 라이브러리 (F11) [Phase 2]
│   ├── calendar/           ← 캘린더 (F10) [Phase 2]
│   ├── analytics/          ← 성과 분석 (F06, F18) [Phase 1-B+]
│   ├── reports/            ← 운영 리포트 (F19) [Phase 3]
│   ├── notifications/      ← 알림 센터 (F13) [Phase 1-B]
│   ├── settings/           ← 설정 (워크플로우, 알림, 기관)
│   ├── audit/              ← 감사 로그 (F14) [Phase 1-B]
│   └── admin/              ← 시스템 관리 (SA 전용)
└── workers/                ← Service Worker (웹 푸시) [Phase 1-B]
```

**의존 규칙:** `features/*` → `shared/*` → 외부 라이브러리. feature 간 직접 import 금지.

### 백엔드

```
app/
├── api/v1/                 ← 19개 도메인 라우터
│   ├── auth.py             ← 7 ep   │ contents.py    ← 17 ep (+6 variant)
│   ├── workspaces.py       ← 2 ep   │ approvals.py   ← 4 ep
│   ├── dashboard.py        ← 8 ep   │ channels.py    ← 7 ep
│   ├── users.py            ← 6 ep   │ settings.py    ← 10 ep
│   ├── search.py           ← 1 ep   │ admin.py       ← 7 ep
│   ├── comments.py [1-B]   ← 8 ep   │ notifications.py [1-B] ← 5 ep
│   ├── reply_templates.py [1-B] ← 4  │ audit_logs.py [1-B] ← 3 ep
│   ├── ai.py [1-B+]        ← 14 ep  │ analytics.py [1-B+]  ← 6 ep
│   ├── calendar.py [P2]    ← 4 ep   │ media.py [P2]  ← 8 ep
│   └── reports.py [P3]     ← 7 ep
├── services/               ← 비즈니스 로직 (트랜잭션 경계)
├── repositories/           ← SQLAlchemy 쿼리 캡슐화
├── models/                 ← SQLAlchemy ORM + RLS
├── schemas/                ← Pydantic 스키마
├── integrations/           ← 외부 서비스
│   ├── platforms/          ← PlatformAdapter (추상) + 5개 어댑터
│   ├── ai/                 ← litellm 래퍼, Whisper 클라이언트
│   ├── telegram/           ← 텔레그램 봇
│   ├── email/              ← FastAPI-Mail + Jinja2 템플릿
│   └── storage/            ← StorageBackend ABC (local/minio) + 레거시 래퍼
├── tasks/                  ← Celery (publish, ai, comment, notification, channel, media, report)
├── core/                   ← 설정, 보안, DB 세션, 예외, 미들웨어
└── migrations/             ← Alembic (RLS 정책 수동 추가)
```

**레이어 규칙:** Router → Service → Repository → Model (단방향만 허용)

---

## 아키텍처 핵심 패턴

### 멀티테넌트

PostgreSQL RLS로 `organization_id` 기반 행 수준 격리.
Workspace 미들웨어가 `SET LOCAL app.current_org_id`로 세션 변수 설정 → 모든 SELECT/INSERT/UPDATE/DELETE가 자동 필터링.
RLS 미적용 테이블: `users`, `organizations`, `roles`, `system_announcements` (전역 데이터).

### 인증/인가

JWT HS256 (access 30분 / refresh 7일), Redis 블랙리스트.
RBAC 4개 역할 + 엔드포인트별 `required_roles` 체크.
로그인 5회 실패 → 30분 잠금 (IP + 계정).

### 실시간 알림

SSE + Redis Pub/Sub (기본) → Web Push (오프라인) → 텔레그램 (긴급) → 이메일 (리포트/초대).
알림 유형별 채널 매핑은 `docs/claude/architecture.md §3` 참조.

### AI 통합

litellm 멀티 프로바이더 라우팅 (GPT-4o → Claude → Gemini Fallback).
10초 이내 작업은 동기, 초과 시 Celery 비동기.
모든 AI 응답에 `confidence`, `model_used`, `processing_time` 메타 포함.

### 비동기 작업

Celery 3큐: `publish` (게시·재시도), `ai` (AI 처리), `system` (토큰 갱신·정리).
지수 백오프 재시도 + Beat 스케줄러 (예약 게시 확인 1m, 대시보드 캐시 5m, 토큰 갱신 1h, 댓글 수집 5m, 만료 세션 정리 6h).

### 플랫폼 연동

`PlatformAdapter` 추상 클래스 → YouTube, Instagram, Facebook, X, 네이버 블로그 5개 구현.
OAuth 토큰 Fernet 암호화 저장, 만료 전 자동 갱신, Rate Limit 중앙 관리.

---

## RBAC 역할 매트릭스

| 약어 | 역할 | 범위 | 핵심 권한 |
|---|---|---|---|
| SA | 시스템 관리자 (System Admin) | 전체 시스템 | 기관 CRUD, 사용자 관리, 시스템 설정, 모니터링 |
| AM | 수탁업체 관리자 (Agency Manager) | 담당 기관들 | 기관 설정, 워크플로우 구성, 사용자 초대, 리포트 |
| AO | 수탁업체 실무자 (Agency Operator) | 담당 기관들 | 콘텐츠 작성, 댓글 대응, 게시 요청, AI 도구 사용 |
| CD | 위탁기관 담당자 (Client Director) | 소속 기관 | 승인/반려, 대시보드 조회, 채널 상태 확인 |

> 모든 엔드포인트는 `required_roles`를 명시. RBAC 체크는 미들웨어(Depends)에서 자동 수행.

---

## Phase 구조

| Phase | 기능 | 핵심 |
|---|---|---|
| **1-A** (최소 MVP) | F08 권한 · F12 채널연동 · F01 통합게시 · F09 승인 | 62개 API, 7개 스프린트 |
| **1-B** (MVP 확장) | F02 AI메타 · F04 댓글 · F06 대시보드확장 · F13 알림 · F07 텔레그램 · F14 감사로그 | +33개 API |
| **2** | F03 자막·효과음 · F05 AI답글 · F10 캘린더 · F11 미디어 · F17 톤변환 · F21 표현검수 · F15 AI숏폼 | +22개 API |
| **3** | F19 리포트 · F18 여론분석 · F20 성과예측 | +9개 API |
| **4** | F16 AI썸네일 · F22 다국어번역 · F23 벤치마크 | +4개 API |

> 합계: 68 + 33 + 22 + 9 + 4 = **136개 API 엔드포인트** (기본 122 + 보강 6 + variant 6 + ffmpeg 영상처리 2)

---

## 설계 문서 참조

| 문서 | 경로 | 핵심 내용 |
|---|---|---|
| 범위 정의서 v1.2 | `docs/프로젝트_범위_정의서.md` | 23개 기능(F01-F23), Phase, RBAC, NFR |
| 화면 설계서 v1.2 | `docs/메뉴_구조_및_화면_설계서.md` | 25개 화면, 6개 흐름도, 메뉴 구조 |
| API 설계서 v1.2 | `docs/API_설계서.md` | 122개 엔드포인트, 응답 구조, 상태 코드 |
| 기술 스택 결정서 v1.2 | `docs/기술_스택_결정서.md` | 72개 기술 선택 근거, Phase 투입 계획 |
| 아키텍처 설계서 v1.1 | `docs/시스템_아키텍처_설계서.md` | 18개 섹션, 시퀀스 다이어그램, ADR 10개 |
| DB 설계서 v1.2 | `docs/데이터베이스_설계서.md` | 33개 테이블 (v2.0: +content_variants, variant_media), 20개 ENUM (+MediaRoleType), RLS 21+10, 마이그레이션 20개 |

---

## Claude Code 부속 파일

상세 정보는 아래 부속 파일에서 확인:

| 파일 | 내용 | 용도 |
|---|---|---|
| [`docs/claude/conventions.md`](docs/claude/conventions.md) | FE/BE 코딩 컨벤션, Git 규칙, 새 기능 체크리스트 | 코드 작성 시 참조 |
| [`docs/claude/architecture.md`](docs/claude/architecture.md) | 8개 아키텍처 영역 상세 패턴 | 구조 설계 시 참조 |
| [`docs/claude/api-quick-ref.md`](docs/claude/api-quick-ref.md) | 122개 API 한 줄 참조 테이블 | API 구현 시 참조 |
| [`docs/claude/implementation-order.md`](docs/claude/implementation-order.md) | 총 22개 스프린트 상세 (Phase 1-A~4) | 구현 순서 결정 시 참조 |

---

## 커밋 컨벤션

```
<type>(<scope>): <subject>

# type: feat | fix | refactor | docs | test | chore | ci | perf
# scope: auth | contents | channels | approvals | dashboard | comments |
#         media | analytics | reports | calendar | notifications |
#         audit | ai | settings | admin | search | infra | shared
# subject: 50자 이내, 현재형, 소문자 시작, 마침표 없음

# 예시:
feat(auth): add JWT refresh token rotation
fix(contents): prevent duplicate publish on retry
refactor(channels): extract PlatformAdapter base class
```

**브랜치 전략:** `main` → `develop` → `feature/<scope>/<description>` → PR → `develop`

---

## 개발 환경 실행

```bash
# 1. 의존성 설치
pnpm install                          # 프론트엔드
pip install -r requirements.txt       # 백엔드

# 2. 인프라 실행
docker compose up -d postgres redis minio  # DB + 캐시 + 파일저장소

# 3. DB 마이그레이션
alembic upgrade head

# 4. 백엔드 서버
uvicorn app.main:app --reload --port 8000

# 5. Celery 워커
celery -A app.tasks worker -Q publish,ai,system --loglevel=info

# 6. 프론트엔드 개발 서버
pnpm dev                              # Vite → http://localhost:5173

# 7. 테스트
pnpm test                             # Vitest (FE 단위)
pnpm test:e2e                         # Playwright (E2E)
pytest                                # pytest (BE 단위)
pytest --cov                          # 커버리지 포함
```

**환경 변수:** `.env.example`을 `.env`로 복사 후 값 설정 (DB URL, Redis URL, JWT Secret, MinIO, AI API Keys).

---

## 빠른 참조: 상태 코드

| 코드 | 의미 | 사용처 |
|---|---|---|
| 200 | OK | 조회, 수정 성공 |
| 201 | Created | 생성 성공 |
| 204 | No Content | 삭제 성공 |
| 400 | Bad Request | 입력 검증 실패 |
| 401 | Unauthorized | 인증 실패 / 토큰 만료 |
| 403 | Forbidden | 권한 부족 / 워크스페이스 접근 불가 |
| 404 | Not Found | 리소스 없음 |
| 409 | Conflict | 중복 (이메일, 슬러그 등) |
| 422 | Unprocessable | Pydantic/FastAPI 검증 실패 (자동) |
| 423 | Locked | 계정 잠금 (5회 실패) |
| 429 | Too Many Requests | Rate Limit 초과 |
| 500 | Internal Server Error | 서버 내부 오류 (Sentry 전송) |
| 502 | Bad Gateway | 외부 플랫폼 API 오류 |
