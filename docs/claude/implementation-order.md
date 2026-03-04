# PubliSync 구현 순서

> Phase 1-A(7개 스프린트), Phase 1-B(6개 스프린트), Phase 2(4개 스프린트), Phase 3(3개 스프린트), Phase 4(2개 스프린트) — 총 22개 스프린트.

---

## Phase 1-A — 최소 MVP (7개 스프린트)

### S1. 프로젝트 초기화 + 인프라 (1주)

**목표:** 개발 환경 완성, Docker Compose 기동, CI 파이프라인 구축

**작업 체크리스트:**

- [ ] 모노레포 디렉토리 구조 생성 (`frontend/`, `backend/`, `docker/`, `docs/`)
- [ ] **FE 초기화:** `pnpm create vite` → React 19 + TypeScript 5 + Vite 6
- [ ] FE 기본 설정: `tailwind.config.ts`, `tsconfig.json`, ESLint flat config, Prettier
- [ ] Ant Design 5 + Tailwind 4 통합 설정 (ConfigProvider, dark mode)
- [ ] **BE 초기화:** `pyproject.toml` → FastAPI + uvicorn + SQLAlchemy 2.0 + Alembic
- [ ] BE 기본 설정: Ruff, mypy, pytest, structlog, Pydantic Settings
- [ ] `app/core/config.py` — 환경 변수 로드 (Pydantic Settings)
- [ ] `app/core/database.py` — AsyncSession 팩토리
- [ ] `app/core/redis.py` — Redis 클라이언트
- [ ] **Docker Compose:** nginx, api, postgres, redis, minio (5개 컨테이너)
- [ ] `docker-compose.dev.yml` — 개발용 (핫 리로드, 볼륨 마운트)
- [ ] Nginx 기본 설정: 리버스 프록시 (/api/* → api:8000), 정적 파일 서빙
- [ ] Let's Encrypt(certbot) 설정 (운영), 개발용 자체 인증서
- [ ] `.env.example` 작성 (전체 환경 변수 목록)
- [ ] **CI 파이프라인:** GitHub Actions — lint, type check, test, 보안 스캔
- [ ] `pre-commit` 설정: trailing-whitespace, ruff, eslint, prettier
- [ ] MinIO 초기 버킷 생성 스크립트 (`publisync-media`)
- [ ] FE: 빈 `App.tsx` + `RouterProvider` + `QueryClientProvider` + `ConfigProvider`
- [ ] BE: `GET /admin/health` 엔드포인트 (DB/Redis 연결 확인)
- [ ] 전체 `docker compose up` 동작 확인

**대상 API (1개):**
1. `GET /admin/health` — 시스템 상태 확인 (DB/Redis 연결)

**대상 테이블:** 없음 (Alembic 초기 설정만)

---

### S2. 인증/권한 F08 핵심 (1.5주)

**목표:** JWT 로그인, RBAC, 멀티테넌트 RLS 기반 구축

**대상 테이블:**
- `users` (id, email, name, password_hash, role, status, failed_login_count, locked_until, preferences)
- `roles` (id, name, permissions)
- `refresh_tokens` (id, user_id, token_hash, expires_at, is_revoked)
- `password_reset_tokens` (id, user_id, token_hash, expires_at, is_used)
- `invitations` (id, email, role, organization_id, token_hash, status, invited_by, expires_at)

> **마이그레이션 매핑:** `002_auth_tables` — 위 5개 테이블 + 인덱스

**대상 API (7개):**
1. `POST /auth/login` — JWT 발급, 5회 실패 잠금
2. `POST /auth/refresh` — 토큰 갱신
3. `POST /auth/logout` — Redis 블랙리스트 추가
4. `POST /auth/password/reset-request` — 이메일 발송
5. `POST /auth/password/reset` — 비밀번호 변경
6. `POST /auth/invite/accept` — 초대 수락 가입
7. `GET /auth/invite/verify` — 초대 토큰 확인

**대상 화면:** 4.16 로그인/인증

**작업 체크리스트:**

- [ ] **모델:** User, Organization, UserOrganization, Role
- [ ] **Alembic 마이그레이션:** 초기 테이블 + SA 시드 데이터
- [ ] `app/core/security.py` — JWT 생성/검증 (python-jose, HS256), bcrypt 해싱
- [ ] `app/core/deps.py` — `get_current_user`, `get_workspace_context`, `require_roles()`
- [ ] **RLS 설정:** organizations 이외 테이블에 RLS 정책 적용
- [ ] `app/core/database.py`에 SQLAlchemy `after_begin` 이벤트 훅 (SET LOCAL)
- [ ] `app/utils/exceptions.py` — PubliSyncError 계층 전체
- [ ] **미들웨어:** CORS, RequestId, RateLimit (slowapi)
- [ ] **서비스:** AuthService (로그인, 갱신, 로그아웃, 비밀번호)
- [ ] **이메일:** FastAPI-Mail 설정, 초대/비밀번호 재설정 Jinja2 템플릿
- [ ] Redis: JWT 블랙리스트, 로그인 실패 카운터
- [ ] **Celery Beat:** 만료 세션 정리 (system 큐, 6시간 주기) — 만료된 refresh_token, 블랙리스트 정리
- [ ] **FE:** LoginPage, ResetPasswordPage, InvitePage
- [ ] FE: Axios 인터셉터 (JWT 주입, 401 자동 갱신, 에러 정규화)
- [ ] FE: `useAuthStore` (Zustand persist), `useWorkspaceStore`
- [ ] FE: RouteGuard 컴포넌트 (인증/역할/워크스페이스 체크)
- [ ] **테스트:** 로그인 성공/실패, 토큰 갱신, 5회 잠금, RLS 격리

---

### S3. 사용자/기관 + 레이아웃 (1.5주)

**목표:** 사용자 CRUD, 기관 CRUD, GlobalLayout (사이드바+상단바)

**대상 테이블:**
- `agencies` (id, name, contact_email, contact_phone, is_active)
- `organizations` (id, name, slug, plan, status, agency_id, settings)
- `user_organizations` (id, user_id, organization_id, role, is_primary) — M:N 매핑
- `workspaces` (id, organization_id, name, is_default)
- `system_announcements` (id, title, content, type, is_active, publish_at, created_by)

> **마이그레이션 매핑:** `003_org_workspace` — 위 5개 테이블 + RLS 정책

**대상 API (18개):**
- 워크스페이스 2개: `GET /workspaces`, `GET /users/me`
- 사용자 6개: `GET/POST/GET/:id/PUT/:id/DELETE/:id /users`, `GET /roles`
- 초대 관리 3개: `GET /users/invitations`, `DELETE /users/invitations/:id`, `POST /users/invitations/:id/resend`
- 설정(기관) 4개: `GET/POST/PUT/:id/DELETE/:id /organizations`
- 대시보드(뱃지) 1개: `GET /dashboard/badge-counts`
- 관리 2개: `GET /admin/agencies`, `POST /admin/agencies`

**대상 화면:** 4.13 사용자·권한, 상단바(워크스페이스 전환), 사이드바

**작업 체크리스트:**

- [ ] **BE:** UserService, UserRepository — CRUD + 초대 이메일 발송
- [ ] **BE:** OrganizationService — CRUD + 사용자 소속 관리
- [ ] **BE:** WorkspaceService — 사용자의 기관 목록, 뱃지 카운트
- [ ] **FE:** GlobalLayout — 사이드바(아이콘+레이블, 접기 가능) + 상단바
- [ ] FE: 상단바 — 워크스페이스 드롭다운 전환기, 프로필, 알림 아이콘
- [ ] FE: 사이드바 — 메뉴 항목, 뱃지 카운트, 역할별 메뉴 필터링
- [ ] FE: UsersPage — 목록(테이블), 초대 모달, 역할 변경, 삭제
- [ ] FE: `useWorkspace` 훅 — X-Workspace-Id 자동 주입
- [ ] 다크 모드 토글 (ConfigProvider + Tailwind 동기화)
- [ ] React Router 라우트 정의 (lazy import, 코드 분할)
- [ ] **테스트:** 워크스페이스 전환, 사용자 CRUD, RBAC 검증

---

### S4. 채널 연동 F12 (1.5주)

**목표:** OAuth 연동, Fernet 토큰 암호화, 자동 갱신

**대상 테이블:**
- `channels` (id, organization_id, platform, platform_account_id, name, status, access_token_enc, refresh_token_enc, token_expires_at, metadata)
- `channel_histories` (id, channel_id, organization_id, event_type, details, actor_id, created_at)

> **마이그레이션 매핑:** `004_channels` — 위 2개 테이블 + RLS + UNIQUE 제약

**대상 API (7개):**
1. `GET /channels` — 연동 채널 목록
2. `POST /channels/connect/initiate` — OAuth 시작 (Authlib)
3. `POST /channels/connect/callback` — OAuth 콜백
4. `DELETE /channels/:id` — 연동 해제
5. `POST /channels/:id/refresh-token` — 토큰 수동 갱신
6. `GET /channels/:id/history` — 연동 이력
7. `GET /channels/api-status` — API Rate Limit 현황

**대상 화면:** 4.12 채널 관리, 4.23 채널 연동 이력

**작업 체크리스트:**

- [ ] **모델:** Channel, ChannelHistory + RLS 정책 (DB 설계서 §3.11~3.12)
- [ ] **PlatformAdapter 추상 클래스** (`integrations/platforms/base.py`)
- [ ] YouTube Adapter (Data API v3, OAuth 2.0) — 최소 publish + get_channel_info
- [ ] 나머지 4개 Adapter 스캐폴드 (스텁 구현, publish만 우선)
- [ ] **Fernet 암호화:** OAuth access_token/refresh_token 암호화 저장
- [ ] **Celery Beat:** 토큰 갱신 확인 (1시간 주기) — 만료 1시간 전 자동 갱신
- [ ] **토큰 상태 머신:** DISCONNECTED → ACTIVE → EXPIRING → EXPIRED
- [ ] Rate Limit Manager (Redis 카운터, 백프레셔)
- [ ] **FE:** ChannelsPage — 채널 목록, 연동 버튼 (OAuth 팝업), 상태 표시
- [ ] FE: ChannelHistoryPage — 연동/해제/갱신 이력 타임라인
- [ ] **테스트:** OAuth 흐름 (모의), 토큰 암호화/복호화, 자동 갱신

---

### S5. 콘텐츠 게시 F01 (2주)

**목표:** CRUD, Celery 비동기 게시, SSE 실시간 상태, 예약 게시

**대상 테이블:**
- `contents` (id, organization_id, title, body, status, channel_ids, platforms, scheduled_at, author_id, platform_contents, metadata, ai_generated, search_vector)
- `content_versions` (id, content_id, organization_id, version, title, body, metadata, changed_by)
- `publish_results` (id, content_id, organization_id, channel_id, status, platform_post_id, platform_url, error_message, views, likes, shares, comments_count)

> **마이그레이션 매핑:** `005_contents` — 위 3개 테이블 + RLS + tsvector 트리거

**대상 API (14개):**
1. `POST /contents` — 콘텐츠 작성
2. `GET /contents` — 목록 (필터/페이지네이션)
3. `GET /contents/:id` — 상세
4. `PUT /contents/:id` — 수정
5. `DELETE /contents/:id` — 삭제
6. `POST /contents/:id/save-draft` — 임시 저장
7. `POST /contents/:id/request-review` — 검토 요청 (F09 연동)
8. `GET /contents/:id/publish-history` — 게시 이력
9. `POST /contents/:id/retry-publish` — 재시도
10. `POST /contents/bulk-action` — 일괄 작업
11. `POST /contents/:id/cancel-publish` — 예약 취소
12. `GET /contents/:id/versions` — 버전 목록
13. `GET /contents/:id/versions/:version` — 특정 버전 상세
14. `POST /contents/:id/versions/:version/restore` — 이전 버전 복원

**대상 화면:** 4.2 콘텐츠 작성, 4.3 목록, 4.17 게시 이력

**작업 체크리스트:**

- [ ] **모델:** Content, ContentVersion, PublishResult + RLS (DB 설계서 §3.13~3.15)
- [ ] **콘텐츠 상태 머신:** DB 설계서 §2 상태 전이 규칙 참조 (12개 상태, PARTIALLY_PUBLISHED 판정 포함)
- [ ] **서비스:** ContentService — CRUD, 상태 전이 검증
- [ ] **Celery 게시 작업:** `publish_content.delay()` — 플랫폼별 병렬 게시
- [ ] 게시 재시도: 지수 백오프 (5m→15m→30m), 최대 3회
- [ ] **SSE 설정:** sse-starlette, Redis Pub/Sub, Nginx SSE 프록시
- [ ] SSE 이벤트: 게시 시작/완료/실패 알림
- [ ] **Celery Beat:** 예약 게시 확인 (1분 주기) — scheduled_at 도달 시 자동 게시
- [ ] react-dropzone: 미디어 업로드 (MinIO 직접 업로드, Presigned URL)
- [ ] **FE:** ContentCreatePage — 에디터, 플랫폼 선택, 미디어 업로드, 예약 설정
- [ ] FE: ContentsListPage — 테이블, 필터 (상태/플랫폼/기간), 일괄 작업
- [ ] FE: 게시 진행 상태 표시 (SSE 수신 → 뱃지/토스트 업데이트)
- [ ] FE: PublishHistoryPage — 게시 이력 타임라인 (성공/실패/재시도)
- [ ] **플랫폼별 콘텐츠 검증:** validate_content() — 글자 수, 비율, 해시태그 규칙
- [ ] **테스트:** 콘텐츠 CRUD, 게시 흐름, 예약 게시, 실패 재시도, SSE 수신

---

### S6. 승인 워크플로우 F09 (1주)

**목표:** 검토 요청 → 검수 → 승인/반려 → 게시 흐름 완성

**대상 테이블:**
- `approval_workflows` (id, organization_id, name, steps JSONB, is_active)
- `approval_requests` (id, content_id, organization_id, workflow_id, current_step, status, requested_by)
- `approval_histories` (id, request_id, organization_id, step, action, reviewer_id, comment)

> **마이그레이션 매핑:** `006_approvals` — 위 3개 테이블 + RLS

**대상 API (6개):**
1. `GET /approvals` — 승인 대기 목록
2. `GET /approvals/:id` — 승인 상세
3. `POST /approvals/:id/approve` — 승인
4. `POST /approvals/:id/reject` — 반려 (사유)
5. `GET /workflows` — 워크플로우 설정 조회
6. `PUT /workflows` — 워크플로우 설정 변경

**대상 화면:** 4.4 승인 대기/검수, 4.21 워크플로우 설정

**작업 체크리스트:**

- [ ] **모델:** ApprovalWorkflow, ApprovalRequest, ApprovalHistory + RLS (DB 설계서 §3.16~3.18)
- [ ] **승인 상태 머신:** PENDING_REVIEW → IN_REVIEW → APPROVED/REJECTED → (REJECTED→DRAFT 수정 후 재요청)
- [ ] 긴급 승인 경로 (Fast Track) — `is_urgent=true` 시 단축 흐름
- [ ] **서비스:** ApprovalService — 검토 요청, 승인, 반려, 이력 기록
- [ ] 승인 완료 → Content 상태를 APPROVED로 변경 → 자동 게시 트리거
- [ ] **SSE 알림:** 검토 요청 시 CD에게, 승인/반려 시 AO에게 실시간 알림
- [ ] **FE:** ApprovalsListPage — 승인 대기 테이블, 긴급 표시
- [ ] FE: ApprovalReviewPage — 콘텐츠 미리보기 + 승인/반려 버튼 + 코멘트
- [ ] FE: WorkflowSettingsPage — 승인 단계 설정, 승인자 지정
- [ ] **테스트:** 승인 흐름, 반려→수정→재요청, 긴급 승인, 권한 검증 (CD만 승인)

---

### S7. 대시보드 + 검색 + 통합 테스트 (1.5주)

**목표:** 대시보드 KPI, 통합 검색, E2E 테스트, Phase 1-A 마무리

**대상 API (9개):**
- 대시보드 6개: `GET /dashboard/summary`, `platform-trends`, `approval-status`, `recent-contents`, `today-schedule`, `all-organizations`
- 검색 1개: `GET /search`
- 관리 2개: `GET /admin/announcements`, `POST /admin/announcements`

**대상 화면:** 4.1 대시보드

**작업 체크리스트:**

- [ ] **BE:** DashboardService — KPI 집계, Redis 캐시 (TTL 5분)
- [ ] 대시보드 데이터 소스: contents(게시 현황), channels(팔로워), approval_requests(대기), publish_results(성과)
- [ ] `GET /dashboard/all-organizations` — AM 전용, 전체 기관 요약
- [ ] `GET /dashboard/badge-counts` — 사이드바 뱃지 (Redis 캐시 30초)
- [ ] **검색:** PostgreSQL tsvector 기반 통합 검색 (콘텐츠, 댓글)
- [ ] 검색 인덱스: `tsvector` 컬럼 + GIN 인덱스
- [ ] **FE:** DashboardPage — KPI 카드 4개, 승인 현황, 최근 콘텐츠, 오늘 스케줄
- [ ] FE: 차트는 Phase 1-B(Recharts)까지 텍스트/숫자로 표시
- [ ] FE: 상단바 검색 — 타이핑 시 debounce 검색 결과 드롭다운
- [ ] **통합 테스트:** Playwright E2E — 로그인→채널연동→콘텐츠작성→검토→승인→게시 흐름
- [ ] 성능 테스트: 대시보드 로딩 < 3초 목표 확인
- [ ] DB 복합 인덱스 최적화 (contents, approvals 테이블)
- [ ] 환경 변수 정리, `.env.example` 최신화
- [ ] Phase 1-A 종료 회고 + Phase 1-B 준비

---

## Phase 1-B — MVP 확장 (6개 스프린트)

### S8. Celery 큐 분할 + AI 메타데이터 F02 (1.5주)

**목표:** Celery 3큐 분할, litellm 도입, AI 제목/설명/해시태그 생성

**대상 테이블:**
- `ai_usage_logs` (id, organization_id, user_id, task_type, model, prompt_tokens, completion_tokens, total_tokens, estimated_cost, processing_time_ms, is_fallback, error_message)

> **마이그레이션 매핑:** `012_ai_logs` — ai_usage_logs + RLS

**대상 API (5개):**
1. `POST /ai/generate-title` — AI 제목 생성 (F02)
2. `POST /ai/generate-description` — AI 설명문 생성 (F02)
3. `POST /ai/generate-hashtags` — AI 해시태그 생성 (F02)
4. `GET /admin/ai-usage` — AI 사용량 모니터링
5. `GET /admin/rate-limits` — Rate Limit 현황

**대상 화면:** 4.2 콘텐츠 작성 (AI 지원 패널 추가)

**작업 체크리스트:**

- [ ] **Celery 큐 분할:** default → `publish` / `ai` / `system` 3큐 분리
- [ ] Celery 워커 설정 업데이트: `--queues publish,ai,system`
- [ ] 기존 Celery 작업 큐 재매핑 (게시→publish, 토큰 갱신→system)
- [ ] **모델:** AiUsageLog + RLS (DB 설계서 §4.6)
- [ ] **litellm 도입:** `integrations/ai/llm_client.py` — litellm 래퍼
- [ ] litellm 설정: model_list (gpt-4o-mini 기본, claude/gemini fallback), 재시도 2회, 타임아웃 10초
- [ ] **서비스:** AiService — 제목/설명/해시태그 생성, 비용 추적, 할당량 관리
- [ ] AI 응답 공통 래퍼: `{ isAiGenerated, confidence, fallbackAvailable, model, suggestions, usage }`
- [ ] **Fallback 로직:** AI 타임아웃/실패 시 "직접 입력하세요" 안내, 수동 입력 경로 보장
- [ ] 기관별 월간 AI 호출 한도 (organizations.settings.features.aiMonthlyQuota)
- [ ] 80% 도달 → 관리자 알림, 100% → AI 비활성화 + Fallback
- [ ] **FE:** ContentCreatePage에 AI 지원 버튼 추가 (제목/설명/해시태그 각각)
- [ ] FE: AI 결과 표시 — 제안 목록, 신뢰도 뱃지, "적용"/"재생성"/"직접 입력" 버튼
- [ ] FE: AI 사용량 대시보드 (`/admin/ai-usage`) — SA 전용
- [ ] **테스트:** AI 생성 성공/실패, Fallback 동작, 할당량 초과, litellm 모의

---

### S9. 댓글 관리 F04 + 답글 템플릿 (2주)

**목표:** 5개 플랫폼 댓글 수집, 감성 분석, 위험 댓글 감지, 답글 템플릿

**대상 테이블:**
- `comments` (id, organization_id, content_id, channel_id, platform, external_id, text, author_name, sentiment, dangerous_level, keywords, status, reply_text, reply_draft, search_vector)
- `templates` (id, organization_id, category, name, content, variables, usage_count, is_active, created_by)

> **마이그레이션 매핑:** `008_comments` — comments + 감성 부분 인덱스 + ENUM(comment_status) + RLS, `009_templates` — templates + RLS
> ⚠️ DB 설계서 표 12.1은 009=notifications, 010=templates이나, 스프린트 순서에 맞춰 재번호 (templates→S9, notifications→S10). DB 설계서 갱신 필요.

**대상 API (12개):**
1. `GET /comments` — 통합 댓글 목록
2. `GET /comments/:id` — 댓글 상세
3. `GET /comments/dangerous` — 위험 댓글 목록
4. `POST /comments/:id/reply` — 댓글 답글
5. `POST /comments/:id/hide` — 댓글 숨김
6. `POST /comments/:id/delete-request` — 댓글 삭제 요청
7. `POST /comments/:id/ignore` — 위험 댓글 무시
8. `POST /comments/:id/delete-approve` — 댓글 삭제 승인
9. `GET /reply-templates` — 템플릿 목록
10. `POST /reply-templates` — 템플릿 생성
11. `PUT /reply-templates/:id` — 템플릿 수정
12. `DELETE /reply-templates/:id` — 템플릿 삭제

**대상 화면:** 4.6 통합 댓글함, 4.7 위험 댓글, 4.20 답글 템플릿 관리

**작업 체크리스트:**

- [ ] **모델:** Comment + RLS (DB 설계서 §4.1), tsvector 트리거
- [ ] **모델:** Template + RLS (DB 설계서 §4.4)
- [ ] **PlatformAdapter 확장:** `get_comments()`, `reply_comment()`, `hide_comment()`, `delete_comment()` 구현 (YouTube, Instagram, Facebook, X)
- [ ] **Celery Beat 작업:** 댓글 수집 (system 큐, 5분 주기) — 플랫폼별 최신 댓글 가져오기
- [ ] **Celery Beat 작업:** 감성 분석 배치 (ai 큐, 10분 주기) — 미분석 댓글 일괄 처리
- [ ] **AI 감성 분석:** gpt-4o-mini — POSITIVE/NEUTRAL/NEGATIVE/DANGEROUS 분류, 신뢰도 점수
- [ ] 위험 댓글 감지: `dangerous_level` (low/medium/high) + 키워드 추출
- [ ] **댓글 상태 머신:** UNPROCESSED → PUBLISHED / HIDDEN / PENDING_DELETE → DELETED
- [ ] **서비스:** CommentService — 목록 조회(필터/페이지네이션), 답글, 숨김, 삭제 요청/승인
- [ ] **서비스:** TemplateService — CRUD, 변수 치환 ({기관명}, {담당자})
- [ ] 답글 시 PlatformAdapter 경유하여 실제 플랫폼에 게시
- [ ] 검색: comments.search_vector tsvector GIN 인덱스
- [ ] **FE:** CommentsListPage — 통합 댓글 테이블, 플랫폼/감성/상태 필터
- [ ] FE: DangerousCommentsPage — 위험 댓글 전용 뷰, 긴급도 뱃지
- [ ] FE: 답글 입력 — 템플릿 선택 드롭다운 + 직접 입력 + 변수 자동 치환
- [ ] FE: TemplatesPage — 템플릿 목록/생성/수정/삭제
- [ ] **가상 스크롤:** @tanstack/react-virtual — 대량 댓글 목록 성능 최적화
- [ ] **테스트:** 댓글 수집(모의), 감성 분석, 답글 게시, 위험 댓글 필터링, 템플릿 CRUD

---

### S10. 알림센터 F13 + 텔레그램 F07 + Web Push (1.5주)

**목표:** 4계층 알림 (SSE/Web Push/텔레그램/이메일), 알림 센터 UI, 사용자별 설정

**대상 테이블:**
- `notifications` (id, organization_id, user_id, type, channel, title, message, payload, is_read, read_at, action_url)
- `notification_settings` (id, organization_id, user_id, channels JSONB, push_subscription, telegram_chat_id)

> **마이그레이션 매핑:** `010_notifications` — 위 2개 테이블 + RLS

**대상 API (9개):**
1. `GET /notifications` — 알림 목록 (필터/페이지네이션)
2. `PATCH /notifications/:id/read` — 알림 읽음 처리
3. `POST /notifications/mark-all-read` — 전체 읽음 처리
4. `GET /notifications/unread-count` — 미읽음 건수
5. `GET /sse/events` — SSE 실시간 스트림
6. `GET /notification-settings` — 알림 설정 조회
7. `PUT /notification-settings` — 알림 설정 변경
8. `POST /notification-settings/telegram/test` — 텔레그램 테스트 발송
9. `POST /notification-settings/telegram/channels` — 텔레그램 채널 설정

**대상 화면:** 4.15 알림 센터 (우측 슬라이드아웃), 4.22 알림 설정 상세

**작업 체크리스트:**

- [ ] **모델:** Notification, NotificationSetting + RLS (DB 설계서 §4.2~4.3)
- [ ] **서비스:** NotificationService — 알림 생성, 읽음 처리, 미읽음 카운트
- [ ] **알림 발송 엔진:** 알림 유형별 채널 매핑 (아키텍처 설계서 §3 참조)
  - SSE: 승인 요청/결과, 위험 댓글, 게시 완료/실패, AI 작업 완료, 토큰 만료
  - Web Push: 승인 요청/결과, 위험 댓글, 게시 실패, 토큰 만료
  - 텔레그램: 승인 요청, 위험 댓글, 게시 실패, 토큰 만료
  - 이메일: 사용자 초대, 비밀번호 재설정, 토큰 만료
- [ ] **SSE 개선:** Phase 1-A의 SSE 기반 확장 — 알림 전용 이벤트 타입 추가
- [ ] **Web Push:** pywebpush — VAPID 키 생성, 구독 관리, 푸시 전송
- [ ] **Service Worker:** `workers/sw.ts` — 웹 푸시 수신, 알림 표시, 클릭 시 해당 페이지 이동
- [ ] **텔레그램 봇:** python-telegram-bot — 봇 초기화, 채널 연동, 메시지 전송
- [ ] 텔레그램 명령어: `/start` (연동), `/status` (현재 알림 설정), `/help`
- [ ] **Celery 작업:** 알림 발송 (system 큐) — 재시도 2회, 고정 30초 백오프
- [ ] 사용자별 알림 설정: 채널별 on/off, 알림 유형별 on/off
- [ ] **FE:** NotificationPanel — 우측 슬라이드아웃, 미읽음 필터, 읽음 처리
- [ ] FE: 상단바 알림 벨 — 미읽음 카운트 뱃지 (SSE 실시간 갱신)
- [ ] FE: NotificationSettingsPage — 채널별/유형별 토글, 텔레그램 연동
- [ ] FE: SSE 수신 훅 — `useSSE` (EventSource + 자동 재연결 + Last-Event-ID)
- [ ] **테스트:** 알림 발송(4채널), 읽음 처리, SSE 재연결, 텔레그램 연동(모의), Web Push(모의)

---

### S11. 감사 로그 F14 + 성과 분석 기반 (1.5주)

**목표:** INSERT-ONLY 감사 로그, 월별 파티셔닝, 성과 스냅샷, CSV 내보내기

**대상 테이블:**
- `audit_logs` (id, organization_id, actor_id, actor_role, action, resource_type, resource_id, changes JSONB, ip_address, user_agent, request_id) — 월별 파티셔닝
- `analytics_snapshots` (id, organization_id, channel_id, platform, snapshot_date, metrics JSONB)

> **마이그레이션 매핑:** `011_audit_logs` — audit_logs (파티셔닝) + INSERT-ONLY 트리거 + RLS, `013_analytics` — analytics_snapshots + RLS + 대시보드 복합 인덱스

**대상 API (6개):**
1. `GET /audit-logs` — 감사 로그 목록
2. `GET /audit-logs/:id` — 감사 로그 상세
3. `GET /audit-logs/export` — 감사 로그 내보내기 (CSV/PDF)
4. `GET /analytics/performance` — 성과 분석 데이터
5. `GET /analytics/engagement-heatmap` — 시간대별 참여율 히트맵
6. `GET /analytics/performance/export` — 성과 데이터 내보내기 (CSV)

**대상 화면:** 4.14 감사 로그, 4.9 성과 분석

**작업 체크리스트:**

- [ ] **모델:** AuditLog + RLS (DB 설계서 §4.5) — PARTITION BY RANGE (created_at)
- [ ] **INSERT-ONLY 트리거:** UPDATE/DELETE 차단 (`prevent_audit_modification()`)
- [ ] **파티션 관리:** 초기 파티션 2개 생성, Celery Beat (매월 1일) 다음 월 파티션 자동 생성
- [ ] 3년 초과 파티션 자동 DROP 함수
- [ ] **모델:** AnalyticsSnapshot + RLS (DB 설계서 §4.7)
- [ ] **감사 로그 자동 기록:** 서비스 레이어 데코레이터/미들웨어 — CUD 작업, 로그인/로그아웃, 승인/연동 이벤트 자동 기록
- [ ] 감사 로그 PII 마스킹: `changes` JSONB 내 이메일, 전화번호 마스킹 처리
- [ ] **서비스:** AuditLogService — 목록 조회 (액션/리소스/기간 필터), CSV/PDF 내보내기
- [ ] **서비스:** AnalyticsService — 성과 데이터 조회, 기간별 집계, CSV 내보내기
- [ ] **Celery Beat 작업:** 플랫폼 데이터 동기화 (system 큐, 1시간 주기) — publish_results 성과 수치 갱신 + analytics_snapshots 일간 스냅샷
- [ ] **FE:** AuditLogPage — 감사 로그 테이블, 필터 (액션/리소스/사용자/기간), 내보내기 버튼
- [ ] FE: 감사 로그 상세 모달 — 변경 전/후 diff 표시
- [ ] FE: AnalyticsPage — 성과 차트 (Recharts), 기간 선택, 플랫폼 필터
- [ ] **가상 스크롤:** @tanstack/react-virtual — 감사 로그 대량 목록 최적화
- [ ] **테스트:** 감사 로그 자동 기록, 파티션 생성, INSERT-ONLY 검증, 성과 조회

---

### S12. 대시보드 고도화 F06 + Recharts (1주)

**목표:** 대시보드 차트 시각화, 감성 분석 현황, Recharts 도입

**대상 API (1개):**
1. `GET /dashboard/sentiment-summary` — 감성 분석 현황 (도넛차트)

**대상 화면:** 4.1 대시보드 (차트 확장)

**작업 체크리스트:**

- [ ] **Recharts 도입:** pnpm add recharts
- [ ] **대시보드 차트 교체:** Phase 1-A의 텍스트/숫자 → 시각 차트
  - KPI 카드: 추이 스파크라인 (미니 라인차트)
  - 플랫폼별 성과 추이: 라인차트 (일별/주별/월별)
  - 승인 현황: 도넛차트 (상태별 비율)
  - 감성 분석 요약: 도넛차트 (POSITIVE/NEUTRAL/NEGATIVE/DANGEROUS)
- [ ] **BE:** DashboardService 확장 — 감성 분석 집계 (comments 테이블 기준)
- [ ] 대시보드 Redis 캐시 갱신: 감성 데이터 포함 (TTL 5분)
- [ ] **FE:** 차트 컴포넌트 분리 — `shared/components/charts/` (LineChart, DonutChart, SparkLine)
- [ ] FE: 대시보드 반응형 — 모바일에서 차트 축소/스와이프
- [ ] **테스트:** 차트 렌더링, 데이터 없을 때 빈 상태, 기간 변경 동작

---

### S13. 모니터링 + 통합 + Phase 1-B 마무리 (1주)

**목표:** Sentry/Flower 도입, Phase 1-B 통합 테스트, 최적화

**작업 체크리스트:**

- [ ] **Sentry 도입:** BE — Sentry SDK, DSN 설정, `before_send` 필터 (PII 제거)
- [ ] Sentry: FE — `@sentry/react`, ErrorBoundary 연동
- [ ] Sentry: Celery 작업 모니터링 — `sentry-sdk[celery]`
- [ ] **Flower 도입:** Celery 워커/큐/작업 실시간 대시보드 (flower:5555)
- [ ] Docker Compose에 Sentry(self-hosted 또는 DSN), Flower 컨테이너 추가
- [ ] **통합 테스트:** Playwright E2E 확장
  - AI 메타데이터 생성 → 콘텐츠 반영 흐름
  - 댓글 수집 → 감성 분석 → 위험 댓글 확인 → 답글 게시 흐름
  - 알림 수신 → 읽음 처리 흐름
  - 감사 로그 자동 기록 확인
- [ ] **성능 최적화:** 대시보드 로딩 < 3초, 댓글 목록 < 2초 (가상 스크롤)
- [ ] 데이터베이스 쿼리 최적화 — EXPLAIN ANALYZE로 느린 쿼리 식별, 인덱스 튜닝
- [ ] 환경 변수 정리: AI API Keys, 텔레그램 봇 토큰, VAPID 키, Sentry DSN
- [ ] `.env.example` Phase 1-B 최신화
- [ ] Phase 1-B 종료 회고 + Phase 2 준비

---

## Phase 2 — AI 콘텐츠 고도화 (4개 스프린트)

### S14. 미디어 라이브러리 F11 + Meilisearch (2주)

**목표:** 미디어 파일 관리, 폴더 구조, Meilisearch 한국어 검색 도입

**대상 테이블:**
- `media_assets` (id, organization_id, file_name, original_name, mime_type, media_type, file_size, storage_path, thumbnail_url, duration, resolution, tags, folder_id, version, created_by)
- `media_folders` (id, organization_id, name, parent_id) — 트리 구조
- `content_media_assets` (id, content_id, media_asset_id, organization_id, sort_order) — M:N
- `search_index_configs` (id, index_name, source_table, sync_fields, last_synced_at, is_active)

> **마이그레이션 매핑:** `014_media_calendar` — 위 4개 테이블 (+ calendar_events, 아래 S15) + RLS

**대상 API (8개):**
1. `GET /media` — 미디어 라이브러리 목록 (필터/페이지네이션)
2. `POST /media/upload` — 미디어 업로드 (multipart, < 50MB 직접 / >= 50MB Presigned URL)
3. `GET /media/:id` — 미디어 상세
4. `PUT /media/:id` — 미디어 메타데이터 수정 (태그, 폴더 이동)
5. `DELETE /media/:id` — 미디어 삭제 (소프트 삭제 → 30일 후 물리 삭제)
6. `GET /media/folders` — 폴더 목록 (트리 구조)
7. `POST /media/folders` — 폴더 생성
8. `POST /media/shortform` — 숏폼 생성 (F15, AI 연동)

**대상 화면:** 4.8 미디어 라이브러리

**작업 체크리스트:**

- [ ] **모델:** MediaAsset, MediaFolder, ContentMediaAsset + RLS (DB 설계서 §5.1~5.2)
- [ ] **모델:** SearchIndexConfig (DB 설계서 §5.4)
- [ ] **서비스:** MediaService — 업로드(소/대용량 분기), CRUD, 폴더 관리
- [ ] **소용량 업로드 (< 50MB):** API Server → MinIO PUT → 201 { mediaId, url }
- [ ] **대용량 업로드 (>= 50MB):** Presigned URL 발급 → 클라이언트 직접 업로드 → 완료 확인
- [ ] **Pillow:** 이미지 리사이징, 썸네일 자동 생성 (200x200)
- [ ] 파일 검증: MIME 타입 확인, 이미지 10MB/영상 2GB 제한, 파일 수 10개 제한
- [ ] **스토리지 할당량:** 기관당 50GB, 80% 경고, 95% 업로드 제한
- [ ] **소프트 삭제 + 물리 삭제:** Celery Beat (일 1회) — 30일 경과 is_deleted=true 파일 MinIO 물리 삭제
- [ ] **Meilisearch 도입:** Docker Compose에 meilisearch 컨테이너 추가
- [ ] Meilisearch 인덱스 설정: contents, comments, media_assets 3개 인덱스
- [ ] 한국어 형태소 분석 설정 (Meilisearch CJK 토크나이저)
- [ ] PostgreSQL tsvector → Meilisearch 마이그레이션: 기존 검색 API 백엔드 교체
- [ ] **Celery Beat 작업:** 스토리지 용량 체크 (system 큐, 일 1회) — 할당량 초과 알림
- [ ] **FE:** MediaLibraryPage — 그리드/리스트 뷰 전환, 폴더 트리 사이드바, 필터 (유형/태그/기간)
- [ ] FE: 업로드 — react-dropzone (드래그앤드롭), 진행률 표시, 대용량 Presigned URL 흐름
- [ ] FE: 미디어 상세 모달 — 메타데이터 편집, 태그 관리, 사용처 표시
- [ ] FE: 콘텐츠 작성 시 미디어 라이브러리에서 선택 가능 (ContentCreatePage 연동)
- [ ] FE: 상단바 검색 — Meilisearch 기반으로 교체, 타이핑 시 인스턴트 검색
- [ ] **테스트:** 업로드(소/대용량), 폴더 CRUD, Meilisearch 검색, 할당량 초과, 삭제 정책

---

### S15. 콘텐츠 캘린더 F10 (1.5주)

**목표:** FullCalendar 기반 예약 게시 캘린더, 공휴일/기념일 관리

**대상 테이블:**
- `calendar_events` (id, organization_id, content_id, title, event_type, event_date, scheduled_at, platform, status, created_by)

> **마이그레이션 매핑:** `014_media_calendar` — S14와 동일 마이그레이션에 포함

**대상 API (4개):**
1. `GET /calendar/events` — 캘린더 이벤트 목록 (월/주/일 범위)
2. `PATCH /calendar/events/:id/reschedule` — 일정 변경 (드래그앤드롭)
3. `GET /calendar/holidays` — 공휴일/기념일 목록
4. `PUT /calendar/holidays` — 공휴일 설정

**대상 화면:** 4.5 캘린더

**작업 체크리스트:**

- [ ] **모델:** CalendarEvent + RLS (DB 설계서 §5.3)
- [ ] **서비스:** CalendarService — 이벤트 목록 (기간 필터), 일정 변경, 공휴일 CRUD
- [ ] 콘텐츠 예약 게시 시 자동으로 calendar_events 생성 (ContentService 연동)
- [ ] 콘텐츠 상태 변경 시 calendar_events 동기화 (게시 완료, 취소 등)
- [ ] 공휴일/기념일 데이터: 한국 공공 데이터 포털 API 또는 수동 등록
- [ ] **FullCalendar 도입:** pnpm add @fullcalendar/core @fullcalendar/react @fullcalendar/daygrid @fullcalendar/timegrid @fullcalendar/interaction
- [ ] **FE:** CalendarPage — 월/주/일 뷰 전환, 플랫폼별 색상 구분
- [ ] FE: 캘린더 이벤트 클릭 → 콘텐츠 상세 모달
- [ ] FE: 드래그앤드롭 일정 변경 → PATCH /calendar/events/:id/reschedule
- [ ] FE: 공휴일/기념일 표시 (배경 하이라이트), 공휴일 설정 모달
- [ ] FE: 새 콘텐츠 생성 — 캘린더에서 날짜 클릭 → 콘텐츠 작성 화면 (날짜 사전 설정)
- [ ] **테스트:** 캘린더 렌더링, 드래그앤드롭 일정 변경, 콘텐츠 연동, 공휴일 표시

---

### S16. AI 고도화 — F05 AI답글 · F17 톤변환 · F21 표현검수 · F03 자막 (2주)

**목표:** AI 답글 초안, 톤앤매너 변환, 표현 가이드 검수, 영상 자막 STT

**대상 API (8개):**
1. `POST /ai/generate-reply` — AI 답글 초안 (F05, 동기 < 10초)
2. `POST /ai/improve-template` — AI 템플릿 개선 (F05, 동기)
3. `POST /ai/tone-transform` — 톤앤매너 변환 (F17, 동기)
4. `POST /ai/content-review` — 표현 가이드 검수 (F21, 동기)
5. `POST /ai/generate-subtitles` — AI 자막 생성 (F03, 비동기 Celery)
6. `POST /ai/suggest-effects` — AI 효과음 제안 (F03, 동기)
7. `POST /ai/extract-shortform` — AI 숏폼 구간 추출 (F15, 비동기 Celery)
8. `GET /ai/jobs/:jobId` — 비동기 AI 작업 상태 조회

**대상 화면:** 4.6 댓글 관리 (AI 답글), 4.2 콘텐츠 작성 (톤변환/검수), 4.18 자막 편집기, 4.19 숏폼 편집

**작업 체크리스트:**

- [ ] **AI 답글 초안 (F05):** gpt-4o-mini — 댓글 맥락 분석, 적절한 톤의 답글 3개 제안
- [ ] AI 답글 Fallback: 실패 시 "직접 작성하세요" + 답글 템플릿 제안
- [ ] **AI 템플릿 개선 (F05):** 기존 답글 템플릿을 AI가 더 자연스럽게 개선
- [ ] **톤앤매너 변환 (F17):** gpt-4o-mini — 공식/친근/유머/격식 등 톤 변환
- [ ] 톤변환 Fallback: 실패 시 원문 그대로 유지
- [ ] **표현 가이드 검수 (F21):** gpt-4o — 4가지 검수 (표현/개인정보/접근성/저작권)
- [ ] 검수 결과: PASS/WARNING/FAIL + 상세 메시지 + 수정 제안
- [ ] 검수 Fallback: 실패 시 "AI 검수 불가, 수동 검수" 안내
- [ ] **자막 생성 (F03):** Whisper API — 영상 음성 → SRT/VTT 자막 (비동기 Celery, 60초 타임아웃)
- [ ] **ffmpeg-python 도입:** 영상에서 오디오 추출 → Whisper API → 자막 파일 생성
- [ ] **비동기 AI 작업 패턴:** 202 Accepted → jobId 반환 → 폴링(3초) 또는 SSE 완료 이벤트
- [ ] **숏폼 구간 추출 (F15):** AI가 하이라이트 구간 제안 → 사용자 확인 후 추출 (비동기)
- [ ] **FE:** 댓글 답글 UI에 "AI 답글 생성" 버튼, 제안 3개 → 선택 → 편집 → 게시
- [ ] FE: 콘텐츠 작성 시 "톤 변환" 버튼, "표현 검수" 버튼 추가
- [ ] FE: 검수 결과 표시 — 항목별 PASS/WARNING/FAIL 뱃지, 수정 제안 표시
- [ ] **Video.js 8 도입:** 영상 재생, 자막 편집기 플레이어
- [ ] **wavesurfer.js 7 도입:** 오디오 파형 표시, 자막 타임라인과 동기화
- [ ] **FE:** SubtitleEditorPage (4.18) — Video.js 8 + wavesurfer.js 7 + 자막 타임라인 편집
- [ ] FE: ShortformEditorPage (4.19) — 구간 선택 UI, AI 제안 구간 표시, 미리보기
- [ ] FE: 비동기 작업 진행 표시 — 프로그레스 바, 완료 시 토스트 알림
- [ ] **테스트:** AI 답글/톤변환/검수(동기), 자막 생성/숏폼 추출(비동기), Fallback 동작, jobId 폴링

---

### S17. Phase 2 통합 + 히트맵 + HA 준비 (1주)

**목표:** Phase 2 통합 테스트, 히트맵 차트, HA 검토

**작업 체크리스트:**

- [ ] **@ant-design/charts 도입:** 히트맵, 워드클라우드용
- [ ] FE: AnalyticsPage에 참여율 히트맵 추가 (시간대 × 요일)
- [ ] **통합 테스트:** Playwright E2E 확장
  - 미디어 업로드 → 콘텐츠 첨부 → 게시 흐름
  - 캘린더 드래그앤드롭 → 예약 변경 확인
  - AI 자막 생성 → 편집 → 저장 흐름
  - AI 답글 생성 → 선택 → 게시 흐름
  - Meilisearch 검색 정확도 검증 (한국어)
- [ ] **HA 준비 검토:** PG Streaming Replication 설정 문서화, Redis Sentinel 구성 계획
- [ ] 데이터베이스 최적화: 미디어/캘린더 관련 쿼리 EXPLAIN ANALYZE
- [ ] Phase 2 종료 회고 + Phase 3 준비

---

## Phase 3 — 분석·보고 고도화 (3개 스프린트)

### S18. AI 리포트 F19 + 리포트 편집기 (2주)

**목표:** AI 자동 운영 리포트 생성, Tiptap 편집기, PDF 다운로드

**대상 테이블:**
- `reports` (id, organization_id, title, period, period_start, period_end, status, content JSONB, pdf_url, generated_by, created_by, finalized_at)

> **마이그레이션 매핑:** `015_reports` — reports + RLS

**대상 API (7개):**
1. `GET /reports` — 리포트 목록
2. `POST /reports/generate` — 리포트 AI 생성 (F19, 비동기 Celery)
3. `GET /reports/:id` — 리포트 상세
4. `PUT /reports/:id` — 리포트 편집
5. `POST /reports/:id/finalize` — 리포트 확정
6. `GET /reports/:id/download` — 리포트 PDF 다운로드
7. `POST /ai/optimal-time` — 최적 게시 시간 추천 (F20)

**대상 화면:** 4.10 운영 리포트

**작업 체크리스트:**

- [ ] **모델:** Report + RLS (DB 설계서 §6.1)
- [ ] **리포트 상태 머신:** DRAFT → GENERATED → FINALIZED
- [ ] **AI 리포트 생성 (F19):** gpt-4o — 기간별 성과 데이터 집계 → 종합 분석 보고서 생성 (비동기 Celery, 300초 타임아웃)
- [ ] 리포트 입력 데이터: analytics_snapshots, publish_results, comments(감성), contents(게시 현황)
- [ ] 리포트 섹션: 요약, 플랫폼별 성과, 콘텐츠 분석, 댓글/여론 분석, 개선 제안
- [ ] AI Fallback: 생성 실패 시 "재시도" 안내, 빈 리포트 템플릿 제공
- [ ] **WeasyPrint PDF 생성:** 리포트 content JSONB → HTML 렌더링 → PDF 파일 → MinIO 저장
- [ ] PDF 템플릿: 기관 로고, 기간, 차트 이미지, 텍스트 섹션
- [ ] **Tiptap v2 도입:** pnpm add @tiptap/react @tiptap/starter-kit — 리포트 편집기
- [ ] **서비스:** ReportService — 생성(AI), 편집, 확정, PDF 다운로드
- [ ] 최적 게시 시간 추천 (F20): analytics_snapshots의 참여율 패턴 분석 → 요일×시간대 추천
- [ ] **FE:** ReportsListPage — 리포트 목록, 상태 필터, 기간 선택
- [ ] FE: ReportEditorPage — Tiptap 에디터 (리치텍스트), 섹션별 편집, AI 재생성 버튼
- [ ] FE: 리포트 미리보기 (PDF와 유사한 레이아웃)
- [ ] FE: PDF 다운로드 버튼 — Blob 다운로드
- [ ] FE: 리포트 생성 중 비동기 진행 표시 (SSE 이벤트)
- [ ] **테스트:** AI 리포트 생성(비동기), 편집/확정 흐름, PDF 생성/다운로드, 최적 시간 추천

---

### S19. 여론 분석 F18 + 성과 예측 F20 (1.5주)

**목표:** 여론 동향 시계열 분석, 위기 확률 예측, 콘텐츠 성과 예측

**대상 API (2개):**
1. `GET /analytics/sentiment-trend` — 여론 동향 시계열 (F18)
2. `GET /analytics/prediction` — 성과 예측 데이터 (F20)

**대상 화면:** 4.11 여론 동향, 4.24 성과 예측

**작업 체크리스트:**

- [ ] **여론 동향 분석 (F18):** comments 감성 데이터 시계열 집계 (일별/주별/월별)
- [ ] 여론 추이 차트: Recharts 라인차트 — POSITIVE/NEUTRAL/NEGATIVE/DANGEROUS 비율 변화
- [ ] 위기 확률 예측: DANGEROUS 비율 급증 감지 → 경고 알림
- [ ] 키워드 추출 트렌드: comments.keywords 빈도 분석 → 워드클라우드
- [ ] **@ant-design/charts 워드클라우드:** 기간별 키워드 빈도 시각화
- [ ] **성과 예측 (F20):** publish_results + analytics_snapshots 데이터 기반
- [ ] 예측 모델: 과거 게시 패턴 분석 → 예상 도달률/참여율 예측 (gpt-4o)
- [ ] 예측 신뢰도: 데이터 축적 3~6개월 미만 시 "데이터 부족" 안내
- [ ] **FE:** SentimentTrendPage — 시계열 차트 (Recharts), 기간 선택, 플랫폼 필터
- [ ] FE: 워드클라우드 차트 (@ant-design/charts)
- [ ] FE: 위기 경고 배너 (DANGEROUS 비율 임계값 초과 시)
- [ ] FE: PredictionPage (4.24) — 성과 예측 차트, 최적 시간대 히트맵, 예측 신뢰도 표시
- [ ] **테스트:** 여론 동향 집계, 워드클라우드 렌더링, 성과 예측 정확도 (데이터 부족 케이스 포함)

---

### S20. 모니터링 스택 + HA + Phase 3 마무리 (1.5주)

**목표:** Prometheus/Grafana/Loki 모니터링, HA 완성, Phase 3 통합 테스트

**작업 체크리스트:**

- [ ] **Prometheus 도입:** Docker Compose에 prometheus 컨테이너 추가
- [ ] FastAPI 메트릭 엔드포인트: `prometheus-fastapi-instrumentator` — 요청 수, 지연시간, 에러율
- [ ] Celery 메트릭: `celery-exporter` — 큐 깊이, 작업 성공/실패, 처리 시간
- [ ] PostgreSQL 메트릭: `postgres_exporter` — 커넥션, 쿼리 지연, 테이블 크기
- [ ] Redis 메트릭: `redis_exporter` — 메모리, 키 수, 히트율
- [ ] **Grafana 도입:** 사전 구성 대시보드 4개 (API, Celery, PostgreSQL, Redis)
- [ ] **Loki 도입:** structlog JSON → Loki 수집 → Grafana에서 로그 검색
- [ ] 알림 규칙: API 에러율 > 5%, Celery 큐 깊이 > 100, DB 커넥션 > 80%
- [ ] **HA 완성:**
  - PostgreSQL Streaming Replication (Primary + Standby)
  - Redis Sentinel (마스터 자동 장애 조치)
  - Nginx upstream health check
- [ ] **통합 테스트:** Playwright E2E 확장
  - AI 리포트 생성 → 편집 → 확정 → PDF 다운로드 흐름
  - 여론 동향 차트 렌더링 + 기간 변경
  - 성과 예측 표시 (데이터 유/무 케이스)
- [ ] 성능 부하 테스트: 동시 사용자 50명 시나리오 (k6 또는 locust)
- [ ] Phase 3 종료 회고 + Phase 4 준비

---

## Phase 4 — 확장 기능 (2개 스프린트)

### S21. AI 썸네일 F16 + 다국어 번역 F22 (1.5주)

**목표:** AI 썸네일 후보 생성, 다국어 번역 (영/중/일/베)

**대상 API (2개):**
1. `POST /ai/generate-thumbnail` — AI 썸네일 생성 (F16, 비동기 Celery)
2. `POST /ai/translate` — AI 다국어 번역 (F22, 동기 < 10초)

**작업 체크리스트:**

- [ ] **AI 썸네일 생성 (F16):** gpt-4o (vision) — 콘텐츠 분석 → 썸네일 레이아웃/색상/텍스트 후보 3개 제안
- [ ] 썸네일 이미지 생성: DALL-E 또는 Stable Diffusion API 연동 (비동기 Celery, 120초 타임아웃)
- [ ] 썸네일 Fallback: 생성 실패 시 기본 템플릿 제공 + 직접 업로드 안내
- [ ] 생성된 썸네일 MinIO 저장 → media_assets 등록
- [ ] **다국어 번역 (F22):** gpt-4o-mini — 한국어 콘텐츠를 영/중/일/베트남어로 번역
- [ ] react-i18next 도입: UI 라벨 다국어 지원 (향후 확장 기반)
- [ ] 번역 Fallback: 실패 시 "번역 불가, 직접 입력" 안내
- [ ] **FE:** 콘텐츠 작성 시 "AI 썸네일 생성" 버튼 → 후보 3개 그리드 → 선택/편집
- [ ] FE: 콘텐츠 작성 시 "번역" 버튼 → 대상 언어 선택 → 번역 결과 탭 표시
- [ ] FE: 번역된 콘텐츠를 platform_contents에 반영 (플랫폼별 개별 편집)
- [ ] **테스트:** 썸네일 생성(비동기), 번역(동기), Fallback 동작, 다국어 UI 전환

---

### S22. 벤치마크 F23 + 최종 통합 (1.5주)

**목표:** 경쟁 벤치마크 분석, 기관 비교, 전체 시스템 최종 통합 테스트

**대상 API (2개):**
1. `GET /analytics/benchmark` — 벤치마크 분석 (F23)
2. `GET /analytics/benchmark/organizations` — 기관 비교 (F23, AM 전용)

**대상 화면:** 4.25 벤치마크 분석

**작업 체크리스트:**

- [ ] **벤치마크 데이터 수집:** Celery Beat (일 1회, system 큐) — 공개 데이터 수집 파이프라인
- [ ] 벤치마크 지표: 업종별 평균 팔로워/참여율/게시 빈도 등 비교
- [ ] **서비스:** BenchmarkService — 벤치마크 데이터 조회, 기관 비교
- [ ] 기관 비교 (AM 전용): 담당 기관 간 성과 비교 차트
- [ ] **FE:** BenchmarkPage (4.25) — 업종 평균 대비 성과 차트, 순위표
- [ ] FE: 기관 비교 뷰 — 멀티 라인차트 (기관별 추이 비교)
- [ ] **전체 통합 테스트:** Playwright E2E — 전체 122개 API 엔드포인트 커버리지 확인
- [ ] 전체 흐름 E2E: 로그인 → 채널연동 → 콘텐츠작성(AI메타+썸네일+검수) → 검토 → 승인 → 게시 → 댓글관리(AI답글) → 리포트생성 → PDF다운로드
- [ ] 성능 종합 테스트: 대시보드 < 3초, 검색 < 1초, AI 동기 < 10초
- [ ] 보안 점검: OWASP Top 10 체크리스트, 의존성 감사 (pip-audit, pnpm audit)
- [ ] 접근성 검사: @axe-core/playwright — critical/serious 위반 0건
- [ ] `.env.example` 최종 최신화 (전체 환경 변수 122개 API 대응)
- [ ] 운영 배포 체크리스트 작성 + 롤백 계획
- [ ] **Phase 4 종료 — 전체 프로젝트 완료**

---

## 스프린트 요약 (전체)

### Phase 1-A — 최소 MVP

| 스프린트 | 내용 | API | 핵심 기술 | 예상 |
|---|---|:---:|---|---|
| S1 | 프로젝트 초기화 + 인프라 | 1 | Docker, Vite, FastAPI, Alembic, CI | 1주 |
| S2 | 인증/권한 F08 | 7 | JWT, bcrypt, RLS, FastAPI-Mail | 1.5주 |
| S3 | 사용자/기관 + 레이아웃 | 18 | RBAC, GlobalLayout, 사이드바, 상단바 | 1.5주 |
| S4 | 채널 연동 F12 | 7 | OAuth, PlatformAdapter, Fernet, Celery Beat | 1.5주 |
| S5 | 콘텐츠 게시 F01 | 14 | Celery, SSE, MinIO, 예약 게시 | 2주 |
| S6 | 승인 워크플로우 F09 | 6 | 상태 머신, Fast Track, SSE 알림 | 1주 |
| S7 | 대시보드 + 검색 + 통합 | 9 | Redis 캐시, tsvector, Playwright E2E | 1.5주 |
| **소계** | | **62** | | **~10주** |

### Phase 1-B — MVP 확장

| 스프린트 | 내용 | API | 핵심 기술 | 예상 |
|---|---|:---:|---|---|
| S8 | Celery 큐 분할 + AI 메타 F02 | 5 | litellm, Celery 3큐, AI Fallback | 1.5주 |
| S9 | 댓글 관리 F04 + 답글 템플릿 | 12 | 감성 분석, PlatformAdapter 확장, 가상 스크롤 | 2주 |
| S10 | 알림센터 F13 + 텔레그램 F07 | 9 | Web Push, pywebpush, python-telegram-bot, SSE | 1.5주 |
| S11 | 감사 로그 F14 + 성과 분석 | 6 | 월별 파티셔닝, INSERT-ONLY, CSV 내보내기 | 1.5주 |
| S12 | 대시보드 고도화 F06 | 1 | Recharts, 라인/도넛/스파크라인 차트 | 1주 |
| S13 | 모니터링 + 통합 + 마무리 | 0 | Sentry, Flower, Playwright E2E | 1주 |
| **소계** | | **33** | | **~8.5주** |

### Phase 2 — AI 콘텐츠 고도화

| 스프린트 | 내용 | API | 핵심 기술 | 예상 |
|---|---|:---:|---|---|
| S14 | 미디어 라이브러리 F11 + Meilisearch | 8 | MinIO 대용량, Pillow, Meilisearch CJK | 2주 |
| S15 | 콘텐츠 캘린더 F10 | 4 | FullCalendar v6, 드래그앤드롭 | 1.5주 |
| S16 | AI 고도화 F05/F17/F21/F03/F15 | 8 | Whisper, ffmpeg-python, Video.js, wavesurfer.js | 2주 |
| S17 | Phase 2 통합 + HA 준비 | 0 | @ant-design/charts, PG Replication 검토 | 1주 |
| **소계** | | **20** | | **~6.5주** |

### Phase 3 — 분석·보고 고도화

| 스프린트 | 내용 | API | 핵심 기술 | 예상 |
|---|---|:---:|---|---|
| S18 | AI 리포트 F19 + 편집기 | 7 | Tiptap v2, WeasyPrint PDF, gpt-4o | 2주 |
| S19 | 여론 분석 F18 + 성과 예측 F20 | 2 | 시계열 분석, 워드클라우드, 예측 모델 | 1.5주 |
| S20 | 모니터링 + HA + 마무리 | 0 | Prometheus, Grafana, Loki, PG Replication, Redis Sentinel | 1.5주 |
| **소계** | | **9** | | **~5주** |

### Phase 4 — 확장 기능

| 스프린트 | 내용 | API | 핵심 기술 | 예상 |
|---|---|:---:|---|---|
| S21 | AI 썸네일 F16 + 다국어 F22 | 2 | gpt-4o vision, DALL-E, react-i18next | 1.5주 |
| S22 | 벤치마크 F23 + 최종 통합 | 2 | 공개 데이터 파이프라인, E2E 전체 커버리지 | 1.5주 |
| **소계** | | **4** | | **~3주** |

### 전체 합계

| Phase | 스프린트 | API | 예상 기간 |
|---|:---:|:---:|---|
| 1-A | S1~S7 (7개) | 62 | ~10주 |
| 1-B | S8~S13 (6개) | 33 | ~8.5주 |
| 2 | S14~S17 (4개) | 20 | ~6.5주 |
| 3 | S18~S20 (3개) | 9 | ~5주 |
| 4 | S21~S22 (2개) | 4 | ~3주 |
| **총합** | **22개 스프린트** | **128** | **~33주** |
