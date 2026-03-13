# PubliSync 코딩 컨벤션

> 이 문서는 5개 설계 문서에서 추출한 코딩 규칙과 패턴을 정리한다.
> 새 코드를 작성할 때 반드시 이 규칙을 따른다.

---

## 1. 프론트엔드 컨벤션

### 1.1 컴포넌트 패턴

- **함수형 컴포넌트만** 사용 (클래스 컴포넌트 금지)
- Props 인터페이스를 컴포넌트 파일 상단에 정의
- 기본 export는 컴포넌트, named export는 타입/훅

```typescript
// ✅ 올바른 패턴
interface ContentCardProps {
  content: Content;
  onEdit: (id: string) => void;
}

export default function ContentCard({ content, onEdit }: ContentCardProps) {
  // ...
}

// ❌ 금지: React.FC, class 컴포넌트, any 타입 props
```

### 1.2 features/ 모듈 구조

각 feature 모듈은 자급자족하며, 교차 의존 금지:

```
features/contents/
├── components/       ← VariantEditor, PlatformPreview, SourceMediaSection 등
├── hooks/            ← useContents, useCreateContent, useVariants
├── pages/            ← ContentsListPage, ContentEditorPage, ContentDetailPage
└── types.ts          ← Content, ContentStatus, VariantRecord 등
```

**의존 방향 규칙:**
```
features/*  ──▶  shared/*  ──▶  외부 라이브러리
    │                │
    │                └── 절대 features/*를 import하지 않음
    │
    └── 다른 features/*를 직접 import하지 않음
        (교차 기능 통신은 shared/hooks 또는 React Router를 경유)
```

- feature A가 feature B의 컴포넌트를 필요로 하면 → **shared/로 승격**하거나 React Router 네비게이션으로 해결

### 1.3 TanStack Query 컨벤션

#### queryKey 규칙

```typescript
// 네이밍: ['도메인', ...필터파라미터]
queryKey: ['contents', { page, status, platform }]
queryKey: ['contents', contentId]
queryKey: ['dashboard', 'summary', { period }]
queryKey: ['comments', 'dangerous']
```

#### 커스텀 훅 네이밍

```typescript
// 조회: use + 도메인 + (선택적 동작)
useContents()           // 목록 조회
useContentDetail(id)    // 단건 조회
useDashboardSummary()   // 대시보드 요약

// 변경: use + 동작 + 도메인
useCreateContent()
useUpdateContent()
useDeleteContent()
useApproveContent()
```

#### 훅 구조 패턴

```typescript
// features/contents/hooks/useContents.ts
export function useContents(filters: ContentFilters) {
  return useQuery({
    queryKey: ['contents', filters],
    queryFn: () => contentApi.getContents(filters),
    select: (data) => data.data,  // 래퍼 해제
  });
}

// features/contents/hooks/useCreateContent.ts
export function useCreateContent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateContentDto) => contentApi.createContent(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });
}
```

#### 글로벌 설정

```typescript
// QueryClient 기본 옵션
{
  staleTime: 30_000,              // 30초
  gcTime: 5 * 60_000,            // 5분
  retry: 2,
  refetchOnWindowFocus: true,
  refetchOnReconnect: true,
}
```

#### Invalidation 규칙

- 콘텐츠 CUD → `['contents']`, `['dashboard']` 무효화
- Variant CUD → `['contents']` 무효화 (콘텐츠 상세에 variants 포함)
- 댓글 변경 → `['comments']`, `['dashboard', 'summary']` 무효화
- SSE 이벤트 수신 → 관련 queryKey 선택적 무효화

### 1.4 Zustand 규칙

**원칙: API 응답 데이터는 절대 Zustand에 저장하지 않는다.** TanStack Query 캐시가 유일한 서버 상태 저장소이다.

```typescript
// stores/useUiStore.ts ← UI 전용 상태만
interface UiState {
  sidebarCollapsed: boolean;
  theme: 'light' | 'dark';
  modalStack: string[];
}

// stores/useWorkspaceStore.ts ← 현재 워크스페이스
interface WorkspaceState {
  currentOrgId: string | null;
  orgList: Organization[];  // 로그인 시 1회 초기화
}

// stores/useAuthStore.ts ← persist 미들웨어 사용
interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
}
```

**상태 유형 분류 매트릭스:**

| 상태 유형 | 관리 도구 | 예시 |
|---|---|---|
| 서버 상태 (캐시) | TanStack Query | 콘텐츠, 댓글, 대시보드 KPI, 채널 목록 |
| 클라이언트 상태 (UI) | Zustand | 사이드바 접힘, 테마, 현재 워크스페이스 |
| URL 상태 | React Router searchParams | 페이지네이션, 필터, 탭 선택 |
| 폼 상태 | React Hook Form + Zod | 콘텐츠 작성 폼, 설정 폼 |

### 1.5 API 호출 (Axios)

#### 인터셉터 체인

```
요청 인터셉터:
  원본 요청 → JWT 주입 (Authorization: Bearer) → Workspace 주입 (X-Workspace-Id) → 서버 전송

응답 인터셉터:
  서버 응답 → 401 감지 → refreshToken 갱신 → 원본 재시도 → 에러 정규화 (ApiError) → toast
```

- 401 수신 시 자동으로 `POST /auth/refresh` 호출 → 성공 시 원본 재시도
- 갱신 실패 → 로그아웃 → 로그인 페이지 리다이렉트
- **동시 요청 경쟁 방지:** 갱신 중인 Promise를 공유하여 중복 갱신 차단

#### API 모듈 위치

- `shared/api/client.ts` — Axios 인스턴스 (baseURL, interceptors)
- `shared/api/types.ts` — `ApiResponse<T>`, `PaginatedResponse<T>`
- `features/*/hooks/` — 도메인별 API 훅 (TanStack Query 래핑)

### 1.6 Ant Design + Tailwind CSS 조합

- **Ant Design 5** — 데이터 컴포넌트 (Table, Form, DatePicker, Tree, Modal, Drawer)
- **Tailwind CSS 4** — 레이아웃 보완 (간격, 정렬, 반응형, 커스텀 스타일)
- **테마 전환:** `ConfigProvider` + `theme.algorithm`으로 light/dark 런타임 전환
- **Tailwind darkMode:** `'selector'` 설정으로 Ant Design 다크 모드와 동기화
- **아이콘:** Lucide React (트리셰이킹, 일관된 스트로크 스타일)

```tsx
// ✅ 올바른 조합
<Card className="mb-4">
  <Table columns={columns} dataSource={data} />
</Card>

// ❌ 금지: Ant Design을 Tailwind로 대체하지 않는다 (Table, Form 등은 반드시 Ant Design)
```

### 1.7 React Hook Form + Zod 폼 패턴

```typescript
// 1. Zod 스키마 정의 (Pydantic 스키마와 1:1 대응)
const contentSchema = z.object({
  title: z.string().min(1, '제목은 필수입니다').max(200),
  body: z.string().min(1),
  platforms: z.array(z.enum(['youtube', 'instagram', 'facebook', 'x', 'naver_blog'])).min(1),
  scheduledAt: z.string().datetime().optional(),
});
type ContentFormData = z.infer<typeof contentSchema>;

// 2. React Hook Form + zodResolver
const form = useForm<ContentFormData>({
  resolver: zodResolver(contentSchema),
  defaultValues: { title: '', body: '', platforms: [] },
});

// 3. Ant Design Controller 래핑
<Controller name="title" control={form.control}
  render={({ field, fieldState }) => (
    <Form.Item label="제목" validateStatus={fieldState.error ? 'error' : ''}
      help={fieldState.error?.message}>
      <Input {...field} />
    </Form.Item>
  )}
/>
```

### 1.8 라우트 가드

```typescript
// RouteGuard 컴포넌트 체크 순서:
// 1. 인증 여부 (accessToken 존재) → 미인증: /login 리다이렉트
// 2. 역할 권한 (requiredRoles 대비) → 권한 부족: 403 페이지
// 3. 워크스페이스 컨텍스트 → 미선택: 워크스페이스 선택 모달
```

- 공개 라우트: `/login`, `/reset-password`, `/invite/:token`
- 코드 분할: `React.lazy + Suspense` — 라우트 단위
- 초기 번들 목표: < 200KB (gzip) — app/, shared/, auth/ 만 포함

### 1.9 에러 처리 (FE)

- API 에러 → `ApiError` 클래스로 정규화 → Ant Design `message.error()` 토스트
- 네트워크 에러 → "네트워크 연결을 확인하세요" 토스트
- 401 → 자동 토큰 갱신 (위 1.5 참조)
- 403 → 권한 없음 페이지 or 토스트
- 429 → "요청이 너무 많습니다. 잠시 후 다시 시도하세요" 토스트

### 1.10 반응형 브레이크포인트

| 브레이크포인트 | 레이아웃 |
|---|---|
| >= 1280px (xl) | 사이드바(펼침) + 메인 + 우측 패널 |
| >= 1024px (lg) | 사이드바(접힘, 아이콘만) + 메인 |
| >= 768px (md) | 하단 탭바 + 풀 화면 콘텐츠 |
| < 768px (모바일) | 하단 탭바 + 단일 컬럼 |

- 모바일: 알림 확인, 승인 처리, 대시보드 KPI, 위험 댓글 대응
- 데스크톱 전용: 콘텐츠 에디터, AI 영상 편집, 리포트 생성, 시스템 관리

### 1.11 접근성 (KWCAG 2.2)

- 모든 이미지에 `alt` 속성
- 색상만으로 정보 구분 금지 (아이콘+텍스트 병행)
- 명도 대비 4.5:1 이상
- 모든 인터랙션 키보드 접근 가능 (Tab, Enter, Esc)
- 시맨틱 HTML5 (`<nav>`, `<main>`, `<aside>`, `<article>`)
- ESLint 플러그인: `eslint-plugin-jsx-a11y`
- CI: `@axe-core/playwright` 자동 검사 (critical/serious 위반 0건 목표)

---

## 2. 백엔드 컨벤션

### 2.1 4-Layer 규칙

| 레이어 | 허용 | 금지 |
|---|---|---|
| **Router** | HTTP 수신, Pydantic 검증, Depends() 주입, 응답 직렬화 | 비즈니스 로직, DB 직접 접근 |
| **Service** | 비즈니스 규칙, 트랜잭션, 다중 Repo 조합, Celery 발행, 외부 호출 조율 | HTTP 객체 참조, 직접 SQL |
| **Repository** | SQLAlchemy 쿼리, CRUD, 페이지네이션, PG 특화 쿼리 | 비즈니스 로직, 외부 서비스 호출 |
| **Model** | ORM 모델 정의, 관계(relationship), RLS 대상 컬럼 | 쿼리, 비즈니스 로직 |

**의존 방향:**
```
Router → Service → Repository → Model
  ↓         ↓          ↓
Schema   Schema    SQLAlchemy Core
(Pydantic)
```

### 2.2 DI 체인 (FastAPI Depends)

```python
# 핵심 의존성 함수 체인
@router.get("/contents")
async def list_contents(
    filters: ContentFilters = Depends(),           # Query params → Pydantic
    user: User = Depends(get_current_user),         # JWT 검증 → User 객체
    workspace: WorkspaceContext = Depends(get_workspace_context),  # org_id + RLS
    service: ContentService = Depends(get_content_service),        # Service 인스턴스
):
    return await service.list_contents(filters)

# DI 체인 해석:
# get_content_service
#   └── get_content_repo
#       └── get_db_session  (AsyncSession, 요청 종료 시 자동 close)
# get_workspace_context
#   └── get_current_user
#       └── get_db_session
```

**핵심 의존성 함수:**

| 함수 | 반환 타입 | 역할 |
|---|---|---|
| `get_db_session` | `AsyncSession` | DB 세션 생성, 요청 종료 시 자동 close |
| `get_current_user` | `User` | JWT → 사용자 조회, 블랙리스트 확인 |
| `get_workspace_context` | `WorkspaceContext` | org_id 추출, RLS 설정, 접근 권한 확인 |
| `require_roles(roles)` | `User` | 역할 목록 대비 현재 사용자 역할 검증 |
| `get_*_service` | `*Service` | 각 도메인 서비스 인스턴스 생성 |

### 2.3 Pydantic 스키마 네이밍

```python
# 패턴: {Domain}{Action}{Request|Response}
# 예시:
ContentCreateRequest      # 콘텐츠 생성 요청
ContentUpdateRequest      # 콘텐츠 수정 요청
ContentResponse           # 콘텐츠 단건 응답
ContentListResponse       # 콘텐츠 목록 응답

# 공통 래퍼
ApiResponse[T]            # { success, data, meta }
PaginatedResponse[T]      # { success, data, meta: { total, page, limit, totalPages } }

# 스키마 파일 위치
app/schemas/common.py     # ApiResponse, PaginatedResponse, ErrorResponse
app/schemas/content.py    # ContentCreateRequest, ContentResponse 등
```

### 2.4 PubliSyncError 예외 계층

```python
PubliSyncError (base)
├── AuthenticationError (401)
│   ├── InvalidCredentialsError       # 이메일/비밀번호 불일치
│   ├── TokenExpiredError             # JWT 만료
│   └── AccountLockedError (423)      # 5회 로그인 실패
├── AuthorizationError (403)
│   ├── InsufficientRoleError         # RBAC 역할 부족
│   └── CrossTenantAccessError        # 타 기관 데이터 접근
├── NotFoundError (404)
│   ├── ContentNotFoundError
│   ├── UserNotFoundError
│   └── ChannelNotFoundError
├── ConflictError (409)
│   ├── DuplicateEmailError
│   └── WorkflowStateConflictError    # 이미 승인된 건 재승인 시도
├── ValidationError (400)
│   └── PlatformConstraintError       # 플랫폼별 제약 위반
├── ExternalServiceError (502)
│   ├── PlatformApiError              # 소셜 미디어 API 오류
│   ├── AiServiceError                # AI API 오류/타임아웃
│   └── EmailDeliveryError            # 이메일 발송 실패
└── RateLimitError (429)
    └── PlatformRateLimitError        # 플랫폼 API Rate Limit 초과
```

**전역 에러 핸들러 등록:**
- `PubliSyncError` → 해당 status_code + 공통 에러 포맷
- `RequestValidationError` → 400 + Pydantic 검증 상세
- `SQLAlchemyError` → 500 + 내부 로그 (사용자에게 상세 미노출)
- `Exception (catch-all)` → 500 + Sentry 전송
- 모든 에러 → structlog로 request_id 포함 로깅

### 2.5 Alembic 마이그레이션 컨벤션

```bash
# 마이그레이션 파일 생성
alembic revision --autogenerate -m "add_comments_table"

# RLS 정책은 autogenerate에서 감지 안 됨 → 수동 추가 필수
# 마이그레이션 파일에 직접 SQL 작성:
op.execute("""
    ALTER TABLE comments ENABLE ROW LEVEL SECURITY;
    ALTER TABLE comments FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON comments
        USING (organization_id = current_setting('app.current_org_id')::uuid);
    CREATE POLICY sa_bypass ON comments
        USING (current_setting('app.user_role', true) = 'SYSTEM_ADMIN');
""")
```

**RLS 체크리스트 (새 테이블 추가 시):**
1. `organization_id` FK 컬럼 추가
2. `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`
3. `tenant_isolation` 정책 생성
4. `sa_bypass` 정책 생성
5. 마이그레이션 리뷰에서 RLS 적용 여부 확인

### 2.6 환경 변수

```python
# app/core/config.py — Pydantic Settings
class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    JWT_SECRET_KEY: str
    OAUTH_ENCRYPTION_KEY: str      # Fernet 키
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    # ... (전체 목록은 .env.example 참조)

    model_config = SettingsConfigDict(env_file=".env")
```

- `.env.example` — Git 추적 (키 이름만, 값 비움)
- `.env` — Git 미추적 (`.gitignore`)
- Docker Compose에서 `env_file: .env`로 주입
- 필수 변수 누락 시 앱 시작 실패 (즉시 감지)

### 2.7 structlog 로깅

```python
# 모든 로그에 request_id 자동 바인딩
logger.info("content_created", content_id=content.id, org_id=org_id)

# 개인정보 자동 마스킹 프로세서:
# 이메일: kim@agency.co.kr → ***@***.kr
# 전화번호: 010-1234-5678 → ***-****-5678
# 적용 범위: structlog, Celery 로그, 에러 트레이스
```

### 2.8 미들웨어 체인 순서

```
Client 요청 → ① CORS → ② RequestId → ③ RateLimit → ④ Auth → ⑤ Workspace → ⑥ RBAC → Router
```

- ①~③: Starlette 미들웨어 (전역)
- ④~⑥: FastAPI `Depends()` 체인 (엔드포인트별)
- 공개 엔드포인트(로그인, 비밀번호 재설정)에서는 ④~⑥ 건너뜀

---

## 3. 공통 컨벤션

### 3.1 Git 브랜치 전략

```
main          ← 프로덕션 (release 태그)
  └── develop ← 통합 (PR 머지 대상)
       ├── feature/auth-login
       ├── feature/content-crud
       ├── fix/token-refresh-race
       └── chore/update-deps
```

- 브랜치명: `{type}/{kebab-case-description}`
- type: `feature`, `fix`, `chore`, `docs`, `refactor`, `test`

### 3.2 커밋 메시지

```
{type}({scope}): {description}

feat(auth): implement JWT login and refresh flow
fix(content): prevent duplicate publish on retry
chore(deps): update TanStack Query to v5.64
refactor(channel): extract PlatformAdapter interface
test(approval): add approval workflow e2e tests
docs(api): update endpoint documentation
```

### 3.3 PR 규칙

- PR 타이틀: 커밋 메시지 형식과 동일
- 변경 파일 수: 가급적 10개 이내 (리뷰 가능 범위)
- CI 체크 통과 필수: 린트, 타입 체크, 테스트, 보안 스캔
- 셀프 리뷰 후 제출

### 3.4 코드 포맷

| 대상 | 도구 | 설정 |
|---|---|---|
| FE 린트 | ESLint (flat config) | TypeScript + React 규칙 |
| FE 포맷 | Prettier | 코드 포맷 통일 |
| BE 린트+포맷 | Ruff | flake8 + isort + black 통합 대체 |
| BE 타입 | mypy (strict) | 정적 타입 분석 |
| Git 훅 | pre-commit | 커밋 전 린트/포맷/타입 자동 실행 |

### 3.5 새 기능 체크리스트

새 기능 또는 새 도메인을 추가할 때 아래 항목을 확인한다:

- [ ] **RLS:** 새 테이블에 `organization_id` + RLS 정책 적용 여부
- [ ] **RBAC:** 엔드포인트에 `require_roles()` Depends 적용 여부
- [ ] **Fallback:** AI 기능이면 수동 대체 경로 존재 여부
- [ ] **감사 로그:** 주요 행위(CUD, 승인, 연동)에 감사 로그 기록 여부
- [ ] **테스트:** 단위 테스트 + 통합 테스트 작성 여부
- [ ] **에러 처리:** PubliSyncError 계층의 적절한 예외 사용 여부
- [ ] **X-Workspace-Id:** 워크스페이스 컨텍스트 필요 API인지 확인
- [ ] **캐시:** Redis 캐시 적용/무효화 대상인지 확인
- [ ] **알림:** 알림 발송이 필요한 이벤트인지 확인 (SSE/Push/텔레그램/이메일)
- [ ] **접근성:** KWCAG 2.2 준수 (alt, 키보드, 대비율)
