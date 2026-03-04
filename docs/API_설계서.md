# PubliSync — API 설계서

> **문서 버전:** v1.2
> **작성일:** 2026-03-04
> **상태:** 초안 (Draft)
> **관련 문서:** 프로젝트_범위_정의서 v1.2, 메뉴_구조_및_화면_설계서 v1.2, 시스템_아키텍처_설계서 v1.1
>
> **변경 이력:**
> | 버전 | 일자 | 변경 내용 |
> |---|---|---|
> | v1.0 | 2026-03-03 | 초기 작성 |
> | v1.1 | 2026-03-03 | 화면 설계서 교차 검증 반영 — 누락 API 13개 추가, 부록 수치 교정, 매핑 테이블 보완 |
> | v1.2 | 2026-03-04 | 아키텍처 설계서 교차 검증 반영 — 공통 상태 코드 423/502 추가, X-Request-Id 추적 헤더 추가 |

---

## 1. 설계 원칙

| 원칙 | 설명 |
|---|---|
| **RESTful** | 리소스 중심 URL 설계, HTTP 메서드(GET/POST/PUT/PATCH/DELETE) 의미에 맞게 사용 |
| **JSON 기반** | 요청·응답 본문은 `application/json` (파일 업로드 제외) |
| **멀티테넌트 격리** | 모든 API는 현재 워크스페이스(위탁기관) 컨텍스트 내에서 동작, `X-Workspace-Id` 헤더로 기관 지정 |
| **RBAC 적용** | 모든 엔드포인트에 역할 기반 접근 제어. 권한 없는 요청은 `403 Forbidden` |
| **일관된 응답 포맷** | 성공/실패 모두 공통 래퍼 구조 사용 |
| **페이지네이션** | 목록 API는 커서 기반 또는 오프셋 기반 페이지네이션 지원 |
| **버전 관리** | URL 경로에 버전 포함: `/api/v1/...` |
| **Phase 연동** | 각 API는 대응 Phase를 명시하여 점진적 구현 가능 |

---

## 2. 공통 사항

### 2.1 기본 URL

```
https://{domain}/api/v1
```

### 2.2 인증 헤더

```
Authorization: Bearer {JWT_ACCESS_TOKEN}
X-Workspace-Id: {organization_id}
X-Request-Id: {uuid-v4}
```

- 로그인·비밀번호 재설정 등 공개 엔드포인트를 제외한 모든 API에 `Authorization` 헤더 필수
- `X-Workspace-Id`는 워크스페이스 컨텍스트가 필요한 API에 필수 (시스템 관리자 전용 API 제외)
- `X-Request-Id`는 요청 추적용 UUID v4 헤더. 클라이언트가 전송하면 그대로 사용하고, 미전송 시 서버가 자동 생성하여 응답 헤더에 포함

### 2.3 공통 응답 구조

**성공 응답:**
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2026-03-03T09:00:00Z"
  }
}
```

**목록 응답 (페이지네이션):**
```json
{
  "success": true,
  "data": [ ... ],
  "meta": {
    "total": 237,
    "page": 1,
    "limit": 20,
    "totalPages": 12,
    "timestamp": "2026-03-03T09:00:00Z"
  }
}
```

**에러 응답:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "제목은 필수 입력 항목입니다.",
    "details": [ ... ]
  },
  "meta": {
    "timestamp": "2026-03-03T09:00:00Z"
  }
}
```

### 2.4 공통 HTTP 상태 코드

| 코드 | 의미 | 사용 상황 |
|---|---|---|
| `200` | 성공 | 조회, 수정 성공 |
| `201` | 생성 성공 | 리소스 생성 성공 |
| `204` | 성공 (본문 없음) | 삭제 성공 |
| `400` | 잘못된 요청 | 파라미터 유효성 검증 실패 |
| `401` | 인증 실패 | 토큰 없음/만료 |
| `403` | 권한 없음 | RBAC 권한 부족, 타 기관 데이터 접근 시도 |
| `404` | 리소스 없음 | 존재하지 않는 리소스 |
| `409` | 충돌 | 중복 생성, 상태 충돌 |
| `423` | 잠김 | 계정 잠금 (5회 이상 로그인 실패) |
| `429` | 요청 과다 | Rate Limit 초과 |
| `500` | 서버 오류 | 예기치 않은 서버 오류 |
| `502` | 외부 서비스 오류 | 소셜 미디어 API, AI API 타임아웃, 이메일 발송 실패 등 외부 서비스 응답 이상 |

### 2.5 역할 약어

| 약어 | 역할 |
|---|---|
| **SA** | 시스템 관리자 (System Admin) |
| **AM** | 수탁업체 관리자 (Agency Manager) |
| **AO** | 수탁업체 실무자 (Agency Operator) |
| **CD** | 위탁기관 담당자 (Client Director) |

---

## 3. 인증 (Authentication)

> **대응 화면:** 4.16 로그인/인증
> **대응 기능:** F08
> **Phase:** 1-A

### 3.1 POST /auth/login — 로그인

**Request Body:**
```json
{
  "email": "user@agency.co.kr",
  "password": "********",
  "rememberMe": false
}
```

**Response 200:**
```json
{
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIs...",
    "refreshToken": "dGhpcyBpcyBhIHJlZnJl...",
    "expiresIn": 3600,
    "user": {
      "id": "usr_abc123",
      "name": "김OO",
      "email": "kim@agency.co.kr",
      "role": "AGENCY_MANAGER",
      "profileImageUrl": "/media/profiles/usr_abc123.jpg",
      "organizations": [
        { "id": "org_001", "name": "서울시 홍보담당관실" },
        { "id": "org_002", "name": "부산시 홍보담당관실" }
      ],
      "defaultOrganizationId": "org_001"
    }
  }
}
```

**Error 401:** 이메일/비밀번호 불일치
**Error 423:** 계정 잠금 (5회 연속 실패)

### 3.2 POST /auth/refresh — 토큰 갱신

**Request Body:**
```json
{
  "refreshToken": "dGhpcyBpcyBhIHJlZnJl..."
}
```

**Response 200:** `accessToken`, `expiresIn` 반환

### 3.3 POST /auth/logout — 로그아웃

**Request:** 헤더의 `Authorization` 토큰 사용
**Response:** `204 No Content`

### 3.4 POST /auth/password/reset-request — 비밀번호 재설정 요청

**Request Body:**
```json
{
  "email": "user@agency.co.kr"
}
```

**Response 200:** `{ "message": "재설정 링크를 이메일로 발송했습니다." }`

### 3.5 POST /auth/password/reset — 비밀번호 재설정

**Request Body:**
```json
{
  "token": "reset_token_from_email",
  "newPassword": "new_password_123!"
}
```

### 3.6 POST /auth/invite/accept — 초대 수락 및 가입

> **대응 흐름:** 5.5 사용자 초대/가입 흐름

**Request Body:**
```json
{
  "inviteToken": "invite_token_from_email",
  "name": "최OO",
  "password": "password_123!"
}
```

**Response 201:** 생성된 사용자 정보 반환

### 3.7 GET /auth/invite/verify — 초대 토큰 유효성 확인

> **대응 흐름:** 5.5 사용자 초대/가입 흐름 — 초대 링크 클릭 시

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `token` | string | Y | 이메일에 포함된 초대 토큰 |

**Response 200:**
```json
{
  "data": {
    "valid": true,
    "email": "new_user@seoul.go.kr",
    "role": "CLIENT_DIRECTOR",
    "organizationName": "서울시 홍보담당관실",
    "invitedBy": "김OO",
    "expiresAt": "2026-03-10T10:00:00Z"
  }
}
```

**Error 400:** 토큰 만료 또는 유효하지 않음
**Error 409:** 이미 수락된 초대

---

## 4. 워크스페이스 (Workspace)

> **대응 화면:** 상단 바 워크스페이스 전환기
> **Phase:** 1-A

### 4.1 GET /workspaces — 현재 사용자의 위탁기관 목록

> 상단 바 워크스페이스 드롭다운에 표시되는 기관 목록

**허용 역할:** SA, AM, AO, CD

**Response 200:**
```json
{
  "data": [
    {
      "id": "org_001",
      "name": "서울시 홍보담당관실",
      "logoUrl": "/media/org/org_001_logo.png",
      "connectedChannelCount": 5,
      "pendingApprovalCount": 3,
      "dangerousCommentCount": 2
    },
    {
      "id": "org_002",
      "name": "부산시 홍보담당관실",
      "logoUrl": "/media/org/org_002_logo.png",
      "connectedChannelCount": 4,
      "pendingApprovalCount": 1,
      "dangerousCommentCount": 0
    }
  ],
  "meta": { "supportsAllOrganizationsView": true }
}
```

> `supportsAllOrganizationsView`는 수탁업체 관리자에게만 `true` — "전체 기관" 뷰 지원 여부

### 4.2 GET /users/me — 로그인 사용자 정보

> 상단 바 프로필 영역, 좌측 사이드바 역할 표시, 워크스페이스 초기 선택에 사용

**허용 역할:** SA, AM, AO, CD

**Response 200:**
```json
{
  "data": {
    "id": "usr_abc123",
    "name": "김OO",
    "email": "kim@agency.co.kr",
    "role": "AGENCY_MANAGER",
    "profileImageUrl": "/media/profiles/usr_abc123.jpg",
    "currentOrganizationId": "org_001",
    "permissions": ["content.create", "content.edit", "content.publish", "comment.manage"],
    "preferences": {
      "theme": "light",
      "language": "ko",
      "defaultView": "dashboard"
    }
  }
}
```

---

## 5. 대시보드 (Dashboard)

> **대응 화면:** 4.1 대시보드
> **대응 기능:** F06 통합 모니터링 대시보드
> **Phase:** 1-A (기본), 1-B (감성분석·KPI 추가)

### 5.1 GET /dashboard/summary — 요약 카드 (KPI)

> 총 팔로워, 총 게시물, 총 댓글, 위험 댓글 수 카드

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `period` | string | N | `7d`, `30d`, `90d` (기본: `7d`) |

**허용 역할:** SA, AM, AO, CD

**Response 200:**
```json
{
  "data": {
    "totalFollowers": { "value": 45200, "changeRate": 3.2, "changeType": "increase" },
    "totalPosts": { "value": 127, "changeCount": 12, "changeType": "increase" },
    "totalComments": { "value": 2341, "changeRate": 18.0, "changeType": "increase" },
    "dangerousComments": { "value": 5, "actionRequired": true }
  }
}
```

### 5.2 GET /dashboard/platform-trends — 플랫폼별 성과 추이

> 라인 차트용 시계열 데이터

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `period` | string | N | `7d`, `30d`, `90d` |
| `metrics` | string | N | `views,likes,shares` (쉼표 구분, 기본: 전체) |

**Response 200:**
```json
{
  "data": {
    "labels": ["03-01", "03-02", "03-03"],
    "platforms": [
      {
        "platform": "youtube",
        "metrics": {
          "views": [1200, 1500, 1800],
          "likes": [45, 60, 72],
          "shares": [10, 15, 20]
        }
      },
      {
        "platform": "instagram",
        "metrics": { "views": [800, 950, 1100], "likes": [120, 140, 160], "shares": [5, 8, 12] }
      }
    ],
    "dataFreshness": {
      "youtube": "2026-03-03T08:58:00Z",
      "instagram": "2026-03-03T08:55:00Z",
      "facebook": "2026-03-03T08:50:00Z",
      "x": "2026-03-03T08:57:00Z",
      "naver_blog": "2026-03-03T08:45:00Z"
    }
  }
}
```

### 5.3 GET /dashboard/approval-status — 승인 대기 현황

**Response 200:**
```json
{
  "data": {
    "pendingReview": 3,
    "rejectedRevision": 1,
    "urgentApproval": 1,
    "items": [
      {
        "id": "cnt_101",
        "title": "서울시 정책 브리핑 3월호",
        "status": "PENDING_REVIEW",
        "isUrgent": true,
        "requester": { "id": "usr_abc", "name": "김OO" },
        "requestedAt": "2026-03-03T09:00:00Z"
      }
    ]
  }
}
```

### 5.4 GET /dashboard/sentiment-summary — 댓글 감성 분석 현황 (Phase 1-B)

> 도넛 차트용 감성 비율 데이터

**Response 200:**
```json
{
  "data": {
    "positive": { "count": 1636, "rate": 62.0, "color": "green" },
    "neutral": { "count": 658, "rate": 28.0, "color": "yellow" },
    "negative": { "count": 42, "rate": 8.0, "color": "orange" },
    "dangerous": { "count": 5, "rate": 2.0, "color": "red" }
  }
}
```

### 5.5 GET /dashboard/recent-contents — 최근 게시 콘텐츠

**Response 200:**
```json
{
  "data": [
    {
      "id": "cnt_100",
      "title": "정책 브리핑 3월호",
      "platform": "youtube",
      "views": 1200,
      "likes": 45,
      "publishedAt": "2026-03-02T09:00:00Z"
    }
  ]
}
```

### 5.6 GET /dashboard/today-schedule — 오늘의 게시 일정

> 캘린더 미니뷰용 데이터

**Response 200:**
```json
{
  "data": [
    {
      "id": "cnt_101",
      "title": "봄맞이 환경정화 캠페인",
      "platform": "instagram",
      "scheduledAt": "2026-03-03T09:00:00Z",
      "status": "PUBLISHED"
    },
    {
      "id": "cnt_102",
      "title": "정책설명회 영상",
      "platform": "youtube",
      "scheduledAt": "2026-03-03T12:00:00Z",
      "status": "PENDING_APPROVAL"
    },
    {
      "id": "cnt_103",
      "title": "교통 안내 트윗",
      "platform": "x",
      "scheduledAt": "2026-03-03T15:00:00Z",
      "status": "SCHEDULED"
    }
  ]
}
```

### 5.7 GET /dashboard/all-organizations — 전체 기관 뷰 (수탁업체 관리자 전용)

**허용 역할:** AM

**Response 200:**
```json
{
  "data": {
    "totalOrganizations": 5,
    "totalChannels": 22,
    "organizationSummaries": [
      {
        "id": "org_001",
        "name": "서울시 홍보담당관실",
        "followers": 45200,
        "posts": 127,
        "pendingApprovals": 3,
        "dangerousComments": 2,
        "engagementRate": 4.2
      }
    ]
  }
}
```

### 5.8 GET /dashboard/badge-counts — 사이드바 뱃지 카운트

> 좌측 사이드바 메뉴 아이콘 옆 뱃지 숫자 표시용 경량 API

**허용 역할:** SA, AM, AO, CD

**Response 200:**
```json
{
  "data": {
    "pendingApprovals": 3,
    "dangerousComments": 5,
    "unreadNotifications": 2,
    "publishFailed": 1,
    "tokenExpiring": 1
  }
}
```

> 사이드바 렌더링 시 1회 호출, 이후 SSE/WebSocket으로 실시간 갱신

---

## 6. 콘텐츠 (Contents)

> **대응 화면:** 4.2 새 콘텐츠 작성, 4.3 콘텐츠 목록, 4.17 게시 이력/실패
> **대응 기능:** F01 통합 게시, F09 승인 워크플로우
> **대응 흐름:** 5.1 콘텐츠 게시 흐름, 5.6 게시 실패 재시도 흐름
> **Phase:** 1-A

### 6.1 POST /contents — 새 콘텐츠 작성

**허용 역할:** AM, AO

**Request Body:**
```json
{
  "title": "서울시 정책 브리핑 3월호",
  "body": "서울시 3월 주요 정책을 안내합니다...",
  "platforms": ["youtube", "instagram", "facebook"],
  "hashtags": ["#서울시", "#정책", "#3월"],
  "mediaIds": ["med_001", "med_002"],
  "platformContents": {
    "youtube": { "title": "서울시 정책 브리핑", "description": "...", "tags": [] },
    "instagram": { "caption": "...", "altText": "..." },
    "facebook": { "message": "..." }
  },
  "scheduleType": "SCHEDULED",
  "scheduledAt": "2026-03-05T09:00:00Z",
  "isUrgent": false
}
```

**Response 201:**
```json
{
  "data": {
    "id": "cnt_201",
    "title": "서울시 정책 브리핑 3월호",
    "status": "DRAFT",
    "platforms": ["youtube", "instagram", "facebook"],
    "createdBy": { "id": "usr_abc", "name": "김OO" },
    "createdAt": "2026-03-03T09:00:00Z",
    "workflowState": "DRAFTING"
  }
}
```

### 6.2 GET /contents — 콘텐츠 목록

> **대응 화면:** 4.3 콘텐츠 목록 — 상태 필터 탭, 플랫폼·기간 필터, 검색, 페이지네이션

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `status` | string | N | `DRAFT`, `PENDING_REVIEW`, `APPROVED`, `PUBLISHED`, `REJECTED`, `ALL` (기본: `ALL`) |
| `platform` | string | N | `youtube`, `instagram`, `facebook`, `x`, `naver_blog` |
| `period` | string | N | `7d`, `30d`, `90d`, `custom` |
| `startDate` | string | N | `period=custom`일 때 시작일 (ISO 8601) |
| `endDate` | string | N | `period=custom`일 때 종료일 |
| `search` | string | N | 제목·본문 키워드 검색 |
| `page` | number | N | 페이지 번호 (기본: 1) |
| `limit` | number | N | 페이지 크기 (기본: 20, 최대: 100) |
| `sortBy` | string | N | `createdAt`, `updatedAt`, `scheduledAt` (기본: `createdAt`) |
| `sortOrder` | string | N | `asc`, `desc` (기본: `desc`) |

**허용 역할:** AM, AO, CD (CD는 조회+검수만)

**Response 200:**
```json
{
  "data": [
    {
      "id": "cnt_201",
      "title": "서울시 정책 브리핑 3월호",
      "status": "PENDING_REVIEW",
      "platforms": ["youtube", "instagram", "facebook"],
      "createdBy": { "id": "usr_abc", "name": "김OO" },
      "createdAt": "2026-03-03T09:00:00Z",
      "scheduledAt": "2026-03-05T09:00:00Z",
      "thumbnailUrl": "/media/thumbnails/cnt_201.jpg"
    }
  ],
  "meta": { "total": 237, "page": 1, "limit": 20, "totalPages": 12 }
}
```

### 6.3 GET /contents/:id — 콘텐츠 상세

**Response 200:**
```json
{
  "data": {
    "id": "cnt_201",
    "title": "서울시 정책 브리핑 3월호",
    "body": "서울시 3월 주요 정책을 안내합니다...",
    "status": "PENDING_REVIEW",
    "platforms": ["youtube", "instagram", "facebook"],
    "hashtags": ["#서울시", "#정책"],
    "media": [
      {
        "id": "med_001",
        "type": "video",
        "url": "/media/files/med_001.mp4",
        "thumbnailUrl": "/media/thumbnails/med_001.jpg",
        "fileName": "정책브리핑.mp4",
        "fileSize": 52428800,
        "duration": 920
      }
    ],
    "platformContents": {
      "youtube": { "title": "...", "description": "...", "tags": [] },
      "instagram": { "caption": "...", "altText": "..." },
      "facebook": { "message": "..." }
    },
    "scheduleType": "SCHEDULED",
    "scheduledAt": "2026-03-05T09:00:00Z",
    "isUrgent": false,
    "workflowState": "PENDING_REVIEW",
    "createdBy": { "id": "usr_abc", "name": "김OO" },
    "createdAt": "2026-03-03T09:00:00Z",
    "updatedAt": "2026-03-03T09:15:00Z",
    "aiReviewResult": {
      "expression": { "status": "PASS", "message": "부적절 표현 없음" },
      "privacy": { "status": "PASS", "message": "개인정보 미검출" },
      "accessibility": { "status": "WARNING", "message": "대체텍스트 미입력 (이미지 2건)" },
      "copyright": { "status": "PASS", "message": "이상 없음" }
    }
  }
}
```

### 6.4 PUT /contents/:id — 콘텐츠 수정

**허용 역할:** AM, AO (본인 작성 건)
**Request Body:** 6.1과 동일 구조 (변경할 필드만 전송)
**Response 200:** 수정된 콘텐츠 상세 반환

### 6.5 DELETE /contents/:id — 콘텐츠 삭제

**허용 역할:** AM, AO (본인 작성 건)
**Response:** `204 No Content`

### 6.6 POST /contents/:id/save-draft — 임시 저장

> **대응 화면:** 4.2 [임시 저장] 버튼

**Request Body:** 6.1과 동일 구조 (부분 데이터 허용)
**Response 200:** 저장된 콘텐츠 상세 반환

### 6.7 POST /contents/:id/request-review — 검토 요청

> **대응 화면:** 4.2 [검토 요청] 버튼
> **대응 흐름:** 5.1 콘텐츠 게시 흐름 — 검토 요청 단계

**허용 역할:** AM, AO

**Request Body:**
```json
{
  "memo": "오늘 15시까지 게시 필요합니다",
  "isUrgent": true,
  "reviewerIds": ["usr_jung"]
}
```

**Response 200:**
```json
{
  "data": {
    "id": "cnt_201",
    "status": "PENDING_REVIEW",
    "workflowState": "PENDING_REVIEW",
    "notificationsSent": { "web": true, "telegram": true }
  }
}
```

### 6.8 GET /contents/:id/publish-history — 게시 이력

> **대응 화면:** 4.17 게시 이력 상세 / 게시 실패

**Response 200:**
```json
{
  "data": {
    "contentId": "cnt_201",
    "platformResults": [
      {
        "platform": "youtube",
        "status": "PUBLISHED",
        "publishedAt": "2026-03-05T09:00:12Z",
        "externalUrl": "https://youtube.com/watch?v=abc",
        "externalId": "yt_video_123"
      },
      {
        "platform": "facebook",
        "status": "FAILED",
        "failedAt": "2026-03-05T09:00:18Z",
        "errorCode": "TOKEN_EXPIRED",
        "errorMessage": "토큰 만료 (Error 190)",
        "retries": [
          { "attempt": 1, "at": "2026-03-05T09:05:00Z", "status": "FAILED" },
          { "attempt": 2, "at": "2026-03-05T09:15:00Z", "status": "FAILED" }
        ],
        "maxRetriesReached": true
      }
    ],
    "notifications": [
      { "type": "web", "sentAt": "2026-03-05T09:00:00Z", "status": "SENT" },
      { "type": "telegram", "sentAt": "2026-03-05T09:01:00Z", "status": "SENT", "recipients": ["김OO", "이OO"] }
    ]
  }
}
```

### 6.9 POST /contents/:id/retry-publish — 수동 재시도

> **대응 화면:** 4.17 [수동 재시도] 버튼

**Request Body:**
```json
{
  "platforms": ["facebook"],
  "refreshTokenFirst": true
}
```

**Response 202:** `{ "data": { "message": "재게시를 요청했습니다.", "jobId": "job_xyz" } }`

### 6.10 POST /contents/bulk-action — 일괄 작업

> **대응 화면:** 4.3 체크박스 선택 후 일괄 작업

**Request Body:**
```json
{
  "contentIds": ["cnt_201", "cnt_202", "cnt_203"],
  "action": "DELETE"
}
```

> `action` 값: `DELETE`, `CHANGE_STATUS`

### 6.11 POST /contents/:id/cancel-publish — 게시 취소

> **대응 흐름:** 5.6 게시 실패 재시도 흐름 — 재시도 포기 시 게시 취소 경로

**허용 역할:** AM, AO (본인 작성 건)

**Request Body:**
```json
{
  "reason": "Facebook 토큰 만료로 인한 게시 불가, 추후 재시도",
  "platforms": ["facebook"]
}
```

**Response 200:**
```json
{
  "data": {
    "id": "cnt_201",
    "status": "CANCELLED",
    "cancelledPlatforms": ["facebook"],
    "remainingPlatforms": ["youtube", "instagram"],
    "cancelledBy": { "id": "usr_abc", "name": "김OO" },
    "cancelledAt": "2026-03-03T10:30:00Z"
  }
}
```

---

## 7. 승인 (Approvals)

> **대응 화면:** 4.4 승인 대기 + 검수 상세
> **대응 기능:** F09 콘텐츠 검수·승인 워크플로우
> **Phase:** 1-A

### 7.1 GET /approvals — 승인 대기 목록

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `tab` | string | N | `MY_REVIEW` (내가 검수할 항목), `MY_REQUEST` (내가 요청한 항목), `ALL` |
| `page` | number | N | 기본: 1 |
| `limit` | number | N | 기본: 20 |

**허용 역할:** AM, AO (본인 건), CD

**Response 200:**
```json
{
  "data": [
    {
      "id": "apv_301",
      "contentId": "cnt_201",
      "title": "서울시 정책 브리핑 3월호",
      "isUrgent": true,
      "requester": { "id": "usr_abc", "name": "김OO" },
      "requestedAt": "2026-03-03T09:00:00Z",
      "platforms": ["youtube", "instagram", "facebook"],
      "memo": "오늘 15시까지 게시 필요합니다",
      "revisionCount": 0,
      "currentStep": "1차 검수"
    }
  ],
  "meta": { "total": 3, "page": 1, "limit": 20, "totalPages": 1 }
}
```

### 7.2 GET /approvals/:id — 검수 상세

> **대응 화면:** 4.4 [검수하기] 클릭 시 — 검수 상세 화면

**Response 200:**
```json
{
  "data": {
    "id": "apv_301",
    "content": {
      "id": "cnt_201",
      "title": "서울시 정책 브리핑 3월호",
      "body": "...",
      "hashtags": ["#서울시"],
      "media": [],
      "platformContents": {},
      "platformPreviews": {
        "youtube": { "previewUrl": "/previews/cnt_201_yt.html" },
        "instagram": { "previewUrl": "/previews/cnt_201_ig.html" },
        "facebook": { "previewUrl": "/previews/cnt_201_fb.html" }
      }
    },
    "aiReviewResult": {
      "expression": { "status": "PASS", "message": "표현 적합성 통과" },
      "privacy": { "status": "PASS", "message": "개인정보 미검출" },
      "accessibility": { "status": "WARNING", "message": "이미지 대체텍스트 미입력 1건" }
    },
    "history": [
      { "action": "CREATED", "actor": { "name": "김OO" }, "at": "2026-03-01T10:00:00Z" },
      { "action": "EDITED", "actor": { "name": "김OO" }, "at": "2026-03-02T14:00:00Z" },
      { "action": "REVIEW_REQUESTED", "actor": { "name": "김OO" }, "at": "2026-03-03T09:00:00Z" }
    ],
    "isUrgent": true,
    "memo": "오늘 15시까지 게시 필요합니다"
  }
}
```

### 7.3 POST /approvals/:id/approve — 승인

**허용 역할:** AM, CD

**Request Body:**
```json
{
  "comment": "확인 완료. 게시 승인합니다."
}
```

**Response 200:**
```json
{
  "data": {
    "id": "apv_301",
    "status": "APPROVED",
    "approvedBy": { "id": "usr_jung", "name": "정OO" },
    "approvedAt": "2026-03-03T10:00:00Z",
    "nextAction": "SCHEDULED_PUBLISH",
    "scheduledAt": "2026-03-05T09:00:00Z"
  }
}
```

### 7.4 POST /approvals/:id/reject — 반려

**허용 역할:** AM, CD

**Request Body:**
```json
{
  "reason": "이미지 해상도가 부족합니다. 고해상도 이미지로 교체해 주세요.",
  "comment": "제목은 좋습니다. 이미지만 수정해 주세요."
}
```

**Response 200:**
```json
{
  "data": {
    "id": "apv_301",
    "status": "REJECTED",
    "rejectedBy": { "id": "usr_jung", "name": "정OO" },
    "rejectedAt": "2026-03-03T10:00:00Z",
    "reason": "이미지 해상도가 부족합니다...",
    "notificationsSent": { "web": true, "telegram": true }
  }
}
```

---

## 8. 캘린더 (Calendar)

> **대응 화면:** 4.5 콘텐츠 캘린더
> **대응 기능:** F10 콘텐츠 캘린더
> **Phase:** 2

### 8.1 GET /calendar/events — 캘린더 이벤트 조회

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `year` | number | Y | 연도 |
| `month` | number | Y | 월 (1~12) |
| `view` | string | N | `monthly`, `weekly`, `daily` (기본: `monthly`) |
| `weekStart` | string | N | `view=weekly`일 때 주 시작일 (ISO 8601) |
| `date` | string | N | `view=daily`일 때 날짜 |
| `platform` | string | N | 플랫폼 필터 |

**허용 역할:** AM, AO, CD (CD는 조회만)

**Response 200:**
```json
{
  "data": {
    "events": [
      {
        "id": "cnt_201",
        "title": "정책 브리핑",
        "platform": "youtube",
        "date": "2026-03-03",
        "scheduledAt": "2026-03-03T12:00:00Z",
        "status": "PENDING_APPROVAL",
        "createdBy": { "name": "김OO" }
      }
    ],
    "conflicts": [
      { "date": "2026-03-09", "count": 3, "message": "동일 시간대 3건 이상 게시 집중" }
    ],
    "holidays": [
      { "date": "2026-03-01", "name": "삼일절" }
    ]
  }
}
```

### 8.2 PATCH /calendar/events/:id/reschedule — 일정 변경 (드래그&드롭)

**Request Body:**
```json
{
  "scheduledAt": "2026-03-10T09:00:00Z"
}
```

**Response 200:** 변경된 이벤트 상세 반환

### 8.3 GET /calendar/holidays — 공휴일·기념일 조회

> **대응 화면:** 4.5 캘린더 — 공휴일·기념일 마커 표시

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `year` | number | Y | 연도 |

**허용 역할:** AM, AO, CD

**Response 200:**
```json
{
  "data": [
    { "date": "2026-01-01", "name": "신정", "type": "PUBLIC_HOLIDAY" },
    { "date": "2026-03-01", "name": "삼일절", "type": "PUBLIC_HOLIDAY" },
    { "date": "2026-03-22", "name": "물의 날", "type": "MEMORIAL_DAY" },
    { "date": "2026-05-05", "name": "어린이날", "type": "PUBLIC_HOLIDAY" }
  ]
}
```

### 8.4 PUT /calendar/holidays — 기념일 사용자 정의 관리

> 기관별 자체 기념일·이벤트 날짜 등록

**허용 역할:** AM

**Request Body:**
```json
{
  "customHolidays": [
    { "date": "2026-04-15", "name": "서울시 정책 설명회", "type": "CUSTOM_EVENT" }
  ]
}
```

**Response 200:** 저장된 공휴일·기념일 목록 반환

---

## 9. 댓글 관리 (Comments)

> **대응 화면:** 4.6 통합 댓글함, 4.7 위험 댓글
> **대응 기능:** F04 통합 댓글 관리, F05 AI 답글 초안
> **대응 흐름:** 5.2 위험 댓글 대응 흐름
> **Phase:** 1-B

### 9.1 GET /comments — 통합 댓글함

> **대응 화면:** 4.6 통합 댓글함 — 감성 필터 탭, 플랫폼 필터, 게시물 필터

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `sentiment` | string | N | `ALL`, `DANGEROUS`, `NEGATIVE`, `NEUTRAL`, `POSITIVE` (기본: `ALL`) |
| `platform` | string | N | 플랫폼 필터 |
| `contentId` | string | N | 특정 게시물의 댓글만 조회 |
| `search` | string | N | 댓글 내용 키워드 검색 |
| `status` | string | N | `UNPROCESSED`, `PROCESSED`, `ARCHIVED` |
| `page` | number | N | 기본: 1 |
| `limit` | number | N | 기본: 30 |

**허용 역할:** AM, AO, CD (CD는 조회+승인)

**Response 200:**
```json
{
  "data": {
    "sentimentCounts": {
      "dangerous": 5,
      "negative": 42,
      "neutral": 658,
      "positive": 1636
    },
    "comments": [
      {
        "id": "cmt_501",
        "platform": "youtube",
        "contentId": "cnt_100",
        "contentTitle": "서울시 정책 브리핑",
        "author": "user123",
        "authorProfileUrl": "https://...",
        "text": "이 정책 당장 철회해라 담당자 나와",
        "sentiment": "DANGEROUS",
        "sentimentScore": 0.94,
        "keywords": ["철회", "담당자"],
        "status": "UNPROCESSED",
        "createdAt": "2026-03-03T08:58:00Z",
        "platformCommentId": "yt_cmt_abc123",
        "parentCommentId": null
      }
    ]
  },
  "meta": { "total": 2341, "page": 1, "limit": 30, "totalPages": 79 }
}
```

### 9.2 GET /comments/:id — 댓글 상세 + 대화 스레드

> **대응 화면:** 4.6 우측 상세 패널

**Response 200:**
```json
{
  "data": {
    "id": "cmt_501",
    "platform": "youtube",
    "content": {
      "id": "cnt_100",
      "title": "서울시 정책 브리핑",
      "externalUrl": "https://youtube.com/watch?v=abc"
    },
    "author": "user123",
    "text": "이 정책 당장 철회해라 담당자 나와",
    "sentiment": "DANGEROUS",
    "sentimentScore": 0.94,
    "keywords": ["철회", "담당자"],
    "status": "UNPROCESSED",
    "createdAt": "2026-03-03T08:58:00Z",
    "thread": [
      {
        "id": "cmt_501",
        "author": "user123",
        "text": "이 정책 당장 철회해라 담당자 나와",
        "createdAt": "2026-03-03T08:58:00Z"
      }
    ],
    "availableActions": {
      "reply": true,
      "hide": true,
      "delete": false,
      "deleteReason": "YouTube API는 댓글 삭제 미지원 (댓글 작성자만 삭제 가능)"
    }
  }
}
```

### 9.3 GET /comments/dangerous — 위험 댓글 목록

> **대응 화면:** 4.7 위험 댓글 관리

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `tab` | string | N | `UNPROCESSED`, `PROCESSED`, `ARCHIVED` (기본: `UNPROCESSED`) |

**Response 200:**
```json
{
  "data": {
    "unprocessedCount": 5,
    "comments": [
      {
        "id": "cmt_501",
        "platform": "youtube",
        "contentTitle": "정책 브리핑 영상",
        "author": "user123",
        "text": "이 정책 당장 철회해라 담당자 나와",
        "sentiment": "DANGEROUS",
        "sentimentScore": 0.94,
        "createdAt": "2026-03-03T08:58:00Z",
        "timeAgo": "2분 전",
        "telegramNotified": true,
        "availableActions": ["AI_REPLY", "HIDE", "DELETE_REQUEST", "IGNORE"]
      }
    ]
  }
}
```

### 9.4 POST /comments/:id/reply — 답글 게시

> **대응 화면:** 4.6 [수정] → [답글 게시] 버튼

**Request Body:**
```json
{
  "text": "안녕하세요, 서울시입니다. 해당 정책에 대한 시민 여러분의 의견을 소중히...",
  "isAiGenerated": true
}
```

**Response 201:**
```json
{
  "data": {
    "id": "cmt_502",
    "parentCommentId": "cmt_501",
    "text": "안녕하세요, 서울시입니다...",
    "postedAt": "2026-03-03T09:10:00Z",
    "platform": "youtube",
    "platformReplyId": "yt_reply_xyz"
  }
}
```

### 9.5 POST /comments/:id/hide — 숨김 처리

**허용 역할:** AM, AO (플랫폼 지원 시)

**Response 200:**
```json
{
  "data": {
    "id": "cmt_501",
    "status": "HIDDEN",
    "processedBy": { "name": "이OO" },
    "processedAt": "2026-03-03T09:15:00Z"
  }
}
```

### 9.6 POST /comments/:id/delete-request — 삭제 승인 요청

> 위탁기관 담당자의 승인이 필요한 경우

**Request Body:**
```json
{
  "reason": "악성 댓글 — 위협성 발언 포함"
}
```

### 9.7 POST /comments/:id/ignore — 무시 (확인됨 처리)

**Request Body:**
```json
{
  "reason": "단순 불만 표현, 대응 불필요로 판단"
}
```

### 9.8 POST /comments/:id/delete-approve — 댓글 삭제 승인 실행

> **대응 화면:** 4.7 위험 댓글 — 삭제 요청(9.6) 이후 위탁기관 담당자가 승인·실행

**허용 역할:** CD

**Request Body:**
```json
{
  "approved": true,
  "comment": "확인 완료, 삭제 승인합니다."
}
```

**Response 200:**
```json
{
  "data": {
    "id": "cmt_501",
    "status": "DELETED",
    "approvedBy": { "id": "usr_jung", "name": "정OO" },
    "approvedAt": "2026-03-03T11:00:00Z",
    "platformDeleteResult": {
      "platform": "youtube",
      "success": true,
      "message": "플랫폼에서 삭제 완료"
    }
  }
}
```

> `approved: false`인 경우 삭제 거부 → 상태가 `UNPROCESSED`로 복귀

---

## 10. 답글 템플릿 (Reply Templates)

> **대응 화면:** 4.20 답글 템플릿 관리
> **대응 기능:** F05 AI 답글 초안 (FAQ 기반 자동 응답 템플릿)
> **Phase:** 1-B (Phase 2에서 AI 연동)

### 10.1 GET /reply-templates — 템플릿 목록

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `category` | string | N | 카테고리 필터 |
| `search` | string | N | 템플릿명·내용 검색 |
| `status` | string | N | `ACTIVE`, `INACTIVE` |

**Response 200:**
```json
{
  "data": [
    {
      "id": "tpl_101",
      "category": "민원·불만",
      "name": "일반 민원 응대",
      "content": "안녕하세요, {기관명}입니다. 불편을 드려 죄송합니다...",
      "variables": ["{기관명}", "{연락처}", "{담당부서}"],
      "usageCount": 124,
      "status": "ACTIVE",
      "updatedAt": "2026-02-15T10:00:00Z"
    }
  ]
}
```

### 10.2 POST /reply-templates — 템플릿 생성

**Request Body:**
```json
{
  "category": "민원·불만",
  "name": "일반 민원 응대",
  "content": "안녕하세요, {기관명}입니다. 불편을 드려 죄송합니다. 해당 사안은 담당 부서에 전달하여 신속히 처리하겠습니다. 추가 문의사항은 {연락처}로 연락 부탁드립니다.",
  "variables": ["{기관명}", "{연락처}", "{담당부서}"],
  "status": "ACTIVE"
}
```

### 10.3 PUT /reply-templates/:id — 템플릿 수정

**Request Body:** 10.2와 동일 구조

### 10.4 DELETE /reply-templates/:id — 템플릿 삭제

**Response:** `204 No Content`

---

## 11. 미디어 라이브러리 (Media)

> **대응 화면:** 4.8 미디어 라이브러리
> **대응 기능:** F11 디지털 자산 관리
> **Phase:** 2

### 11.1 GET /media — 파일 목록

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `folderId` | string | N | 폴더 ID (미지정 시 루트) |
| `type` | string | N | `video`, `image`, `document`, `ALL` |
| `tag` | string | N | 태그 필터 |
| `search` | string | N | 파일명·태그 검색 |
| `sortBy` | string | N | `createdAt`, `name`, `size` (기본: `createdAt`) |
| `sortOrder` | string | N | `asc`, `desc` |
| `view` | string | N | `grid`, `list` (기본: `grid`) |
| `page` | number | N | 기본: 1 |
| `limit` | number | N | 기본: 40 |

**허용 역할:** AM, AO, CD (CD는 조회만)

**Response 200:**
```json
{
  "data": {
    "files": [
      {
        "id": "med_001",
        "type": "video",
        "fileName": "정책브리핑.mp4",
        "fileSize": 52428800,
        "thumbnailUrl": "/media/thumbnails/med_001.jpg",
        "version": "v2",
        "tags": ["정책", "3월"],
        "usedInContents": ["cnt_201"],
        "createdBy": { "name": "김OO" },
        "createdAt": "2026-03-01T10:00:00Z"
      }
    ],
    "storageUsage": {
      "used": 13207642112,
      "quota": 53687091200,
      "usedFormatted": "12.3GB",
      "quotaFormatted": "50GB"
    }
  },
  "meta": { "total": 156, "page": 1, "limit": 40, "totalPages": 4 }
}
```

### 11.2 POST /media/upload — 파일 업로드

**Content-Type:** `multipart/form-data`

**Form Fields:**

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `file` | File | Y | 업로드할 파일 |
| `folderId` | string | N | 대상 폴더 ID |
| `tags` | string | N | 쉼표 구분 태그 |

**Response 201:**
```json
{
  "data": {
    "id": "med_010",
    "type": "image",
    "fileName": "캠페인_포스터.png",
    "fileSize": 2048000,
    "url": "/media/files/med_010.png",
    "thumbnailUrl": "/media/thumbnails/med_010.jpg",
    "version": "v1"
  }
}
```

### 11.3 GET /media/:id — 파일 상세

> **대응 화면:** 4.8 파일 클릭 시 상세 패널

**Response 200:**
```json
{
  "data": {
    "id": "med_001",
    "type": "video",
    "fileName": "정책브리핑.mp4",
    "fileSize": 52428800,
    "url": "/media/files/med_001.mp4",
    "thumbnailUrl": "/media/thumbnails/med_001.jpg",
    "mimeType": "video/mp4",
    "duration": 920,
    "resolution": "1920x1080",
    "tags": ["정책", "3월"],
    "versions": [
      { "version": "v1", "createdAt": "2026-02-28T10:00:00Z", "fileSize": 48000000 },
      { "version": "v2", "createdAt": "2026-03-01T10:00:00Z", "fileSize": 52428800 }
    ],
    "usedInContents": [
      { "id": "cnt_201", "title": "서울시 정책 브리핑 3월호" }
    ],
    "createdBy": { "name": "김OO" },
    "createdAt": "2026-02-28T10:00:00Z",
    "updatedAt": "2026-03-01T10:00:00Z"
  }
}
```

### 11.4 PUT /media/:id — 파일 메타 수정 (태그 편집 등)

**Request Body:**
```json
{
  "tags": ["정책", "3월", "브리핑"],
  "fileName": "정책브리핑_최종.mp4"
}
```

### 11.5 DELETE /media/:id — 파일 삭제

**Response:** `204 No Content`

### 11.6 GET /media/folders — 폴더 트리

**Response 200:**
```json
{
  "data": [
    {
      "id": "fld_001",
      "name": "2026년 3월",
      "parentId": null,
      "children": [
        { "id": "fld_002", "name": "영상", "parentId": "fld_001", "children": [], "fileCount": 12 },
        { "id": "fld_003", "name": "이미지", "parentId": "fld_001", "children": [], "fileCount": 45 },
        { "id": "fld_004", "name": "문서", "parentId": "fld_001", "children": [], "fileCount": 8 }
      ],
      "fileCount": 65
    },
    { "id": "fld_010", "name": "템플릿", "parentId": null, "children": [], "fileCount": 15 }
  ]
}
```

### 11.7 POST /media/folders — 폴더 생성

**Request Body:**
```json
{
  "name": "2026년 4월",
  "parentId": null
}
```

### 11.8 POST /media/shortform — 숏폼 미디어 저장

> **대응 화면:** 4.19 AI 숏폼 편집 — 편집 완료 후 저장
> AI 추출(18.9) 후 사용자가 편집·확정한 숏폼을 미디어 라이브러리에 저장

**허용 역할:** AM, AO

**Request Body:**
```json
{
  "sourceMediaId": "med_001",
  "startTime": "00:00:30",
  "endTime": "00:01:15",
  "title": "핵심 정책 요약 숏폼",
  "subtitles": [
    { "index": 1, "startTime": "00:00:00", "endTime": "00:00:05", "text": "서울시 정책 핵심 요약" }
  ],
  "tags": ["숏폼", "정책", "3월"]
}
```

**Response 201:**
```json
{
  "data": {
    "id": "med_020",
    "type": "video",
    "fileName": "핵심_정책_요약_숏폼.mp4",
    "fileSize": 8500000,
    "duration": 45,
    "sourceMediaId": "med_001",
    "url": "/media/files/med_020.mp4",
    "thumbnailUrl": "/media/thumbnails/med_020.jpg"
  }
}
```

---

## 12. 분석·리포트 (Analytics & Reports)

> **대응 화면:** 4.9 성과 분석, 4.10 운영 리포트, 4.11 여론 동향, 4.24 성과 예측, 4.25 벤치마크 분석
> **대응 기능:** F06, F18, F19, F20, F23

### 12.1 GET /analytics/performance — 성과 분석 (Phase 1-B)

> **대응 화면:** 4.9 성과 분석

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `startDate` | string | Y | 시작일 (ISO 8601) |
| `endDate` | string | Y | 종료일 |
| `platform` | string | N | 플랫폼 필터 |
| `granularity` | string | N | `daily`, `weekly`, `monthly` (기본: `daily`) |

**허용 역할:** AM, AO, CD

**Response 200:**
```json
{
  "data": {
    "summary": {
      "totalReach": { "value": 125400, "changeRate": 12.3 },
      "engagementRate": { "value": 4.2, "changePoint": 0.8 },
      "totalFollowers": { "value": 45200, "changeCount": 1423 },
      "totalPosts": { "value": 127, "changeCount": 15 }
    },
    "trendData": {
      "labels": ["2026-02-01", "2026-02-02"],
      "platforms": [
        {
          "platform": "youtube",
          "reach": [3200, 3500],
          "engagement": [120, 145],
          "followers": [15200, 15250]
        }
      ]
    },
    "platformComparison": [
      { "platform": "youtube", "reach": 45000, "engagement": 4.5, "followers": 15200 },
      { "platform": "instagram", "reach": 32000, "engagement": 5.2, "followers": 12500 }
    ],
    "topContents": [
      {
        "id": "cnt_100",
        "title": "정책 브리핑",
        "platform": "youtube",
        "reach": 12300,
        "likes": 245,
        "publishedAt": "2026-02-20T09:00:00Z"
      }
    ]
  }
}
```

### 12.2 GET /analytics/engagement-heatmap — 시간대별 참여율 히트맵 (Phase 1-B)

> **대응 화면:** 4.9 게시 시간대별 참여율 히트맵

**Response 200:**
```json
{
  "data": {
    "matrix": [
      { "dayOfWeek": "MON", "hours": { "9": 4.2, "10": 3.8, "11": 2.1 } },
      { "dayOfWeek": "TUE", "hours": { "9": 5.1, "10": 4.5, "11": 3.2 } }
    ],
    "optimalSlots": [
      { "dayOfWeek": "TUE", "hour": 9, "engagementRate": 5.1 },
      { "dayOfWeek": "THU", "hour": 14, "engagementRate": 4.8 }
    ]
  }
}
```

### 12.3 GET /analytics/sentiment-trend — 여론 동향 (Phase 3)

> **대응 화면:** 4.11 여론 동향

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `period` | string | N | `7d`, `30d`, `90d` |

**Response 200:**
```json
{
  "data": {
    "alerts": [
      {
        "id": "alert_001",
        "keyword": "교통정책",
        "type": "NEGATIVE_SURGE",
        "changeRate": 230.0,
        "timeframe": "48시간",
        "riskLevel": "HIGH",
        "confidence": "MODERATE",
        "message": "\"교통정책\" 키워드 부정 댓글 48시간 내 230% 급증"
      }
    ],
    "sentimentTrend": {
      "labels": ["03-01", "03-02", "03-03"],
      "positive": [62, 60, 58],
      "neutral": [28, 29, 30],
      "negative": [8, 9, 10],
      "dangerous": [2, 2, 2]
    },
    "keywordCloud": [
      { "keyword": "교통", "count": 89, "sentiment": "NEGATIVE", "change": 230 },
      { "keyword": "정책", "count": 76, "sentiment": "NEUTRAL", "change": 15 },
      { "keyword": "환경", "count": 54, "sentiment": "POSITIVE", "change": 10 }
    ],
    "keywordFrequencyTrend": [
      { "keyword": "교통", "data": [10, 25, 89] },
      { "keyword": "정책", "data": [50, 65, 76] }
    ]
  }
}
```

### 12.4 GET /reports — 운영 리포트 목록 (Phase 3)

> **대응 화면:** 4.10 운영 리포트

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `type` | string | N | `WEEKLY`, `MONTHLY` |
| `status` | string | N | `DRAFT`, `FINALIZED` |

**Response 200:**
```json
{
  "data": [
    {
      "id": "rpt_001",
      "title": "2월 5주차 주간 운영 리포트",
      "type": "WEEKLY",
      "periodStart": "2026-02-24",
      "periodEnd": "2026-03-02",
      "status": "FINALIZED",
      "finalizedAt": "2026-03-03T10:00:00Z",
      "createdAt": "2026-03-03T08:00:00Z"
    }
  ]
}
```

### 12.5 POST /reports/generate — AI 리포트 생성 (Phase 3)

> **대응 화면:** 4.10 [🤖 새 리포트 생성] 버튼
> **대응 흐름:** 5.3 운영 리포트 생성 흐름

**Request Body:**
```json
{
  "type": "WEEKLY",
  "periodStart": "2026-02-24",
  "periodEnd": "2026-03-02",
  "includeSections": ["KPI_SUMMARY", "PLATFORM_PERFORMANCE", "TOP_CONTENTS", "COMMENT_ANALYSIS", "AI_SUGGESTIONS"]
}
```

**Response 202:**
```json
{
  "data": {
    "jobId": "job_rpt_001",
    "status": "GENERATING",
    "estimatedSeconds": 30,
    "message": "AI 리포트를 생성 중입니다..."
  }
}
```

### 12.6 GET /reports/:id — 리포트 상세 (Phase 3)

**Response 200:**
```json
{
  "data": {
    "id": "rpt_001",
    "title": "2월 5주차 주간 운영 리포트",
    "type": "WEEKLY",
    "status": "DRAFT",
    "sections": {
      "summary": { "type": "AI_TEXT", "content": "이번 주 총 게시물 32건, 전주 대비 +12%..." },
      "platformPerformance": { "type": "CHART_DATA", "data": {} },
      "topContents": { "type": "TABLE_DATA", "data": [] },
      "commentAnalysis": { "type": "CHART_DATA", "data": {} },
      "aiSuggestions": { "type": "AI_TEXT", "content": "Instagram 릴스 게시 빈도를 높이면..." }
    }
  }
}
```

### 12.7 PUT /reports/:id — 리포트 편집 (Phase 3)

**Request Body:** 섹션별 텍스트 편집 내용

### 12.8 POST /reports/:id/finalize — 리포트 확정 (Phase 3)

**Response 200:** `{ "data": { "status": "FINALIZED", "finalizedAt": "..." } }`

### 12.9 GET /reports/:id/download — 리포트 PDF 다운로드 (Phase 3)

**Response:** `Content-Type: application/pdf` 바이너리 스트림

### 12.10 GET /analytics/prediction — 콘텐츠 성과 예측 (Phase 3)

> **대응 화면:** 4.24 콘텐츠 성과 예측

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `contentId` | string | Y | 예측 대상 콘텐츠 ID |

**Response 200:**
```json
{
  "data": {
    "isBeta": true,
    "contentId": "cnt_201",
    "platformPredictions": [
      {
        "platform": "youtube",
        "estimatedViews": { "min": 1200, "max": 2500 },
        "estimatedLikes": { "min": 45, "max": 80 }
      },
      {
        "platform": "instagram",
        "estimatedReach": { "min": 800, "max": 1500 },
        "estimatedEngagementRate": { "min": 3.2, "max": 4.5 }
      }
    ],
    "optimalPublishTimes": [
      { "dayOfWeek": "TUE", "timeRange": "09:00~10:00", "reason": "최근 3개월간 유사 콘텐츠 성과 분석" },
      { "dayOfWeek": "THU", "timeRange": "14:00~15:00", "reason": "최근 3개월간 유사 콘텐츠 성과 분석" }
    ],
    "abTestSuggestions": [
      {
        "field": "title",
        "optionA": "서울시 3월 정책 브리핑 — 핵심 요약",
        "optionB": "3분 만에 보는 서울시 3월 정책 변화",
        "prediction": "옵션 B가 CTR 15~20% 높을 것으로 예측",
        "reason": "\"숫자 + 짧은 시간\" 키워드 포함 콘텐츠의 평균 클릭률이 18% 높음"
      }
    ]
  }
}
```

### 12.11 GET /analytics/benchmark — 벤치마크 분석 (Phase 4)

> **대응 화면:** 4.25 벤치마크 분석

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `compareOrganizationIds` | string | Y | 비교 대상 기관 ID (쉼표 구분) |
| `period` | string | N | `30d`, `90d` |

**Response 200:**
```json
{
  "data": {
    "comparison": [
      {
        "organizationId": "org_001",
        "name": "서울시",
        "followers": 45200,
        "posts": 127,
        "engagementRate": 4.2,
        "growthRate": 3.2
      },
      {
        "organizationId": "org_ext_busan",
        "name": "부산시",
        "followers": 32100,
        "posts": 98,
        "engagementRate": 3.8,
        "growthRate": 5.1
      }
    ],
    "aiInsights": [
      {
        "organizationName": "부산시",
        "insight": "이번 달 릴스 조회수 300% 증가. 사용된 포맷: 시민 참여형 챌린지 영상",
        "actionable": true
      }
    ],
    "disclaimer": "공개 데이터(조회수, 좋아요 등)만 수집하며, 비공개 데이터는 포함되지 않습니다."
  }
}
```

### 12.12 GET /analytics/performance/export — 성과 분석 PDF 내보내기 (Phase 1-B)

> **대응 화면:** 4.9 성과 분석 — [PDF 내보내기] 버튼

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `startDate` | string | Y | 시작일 (ISO 8601) |
| `endDate` | string | Y | 종료일 |
| `platform` | string | N | 플랫폼 필터 |
| `format` | string | Y | `pdf` |

**허용 역할:** AM, AO, CD

**Response:** `Content-Type: application/pdf` 바이너리 스트림

### 12.13 GET /analytics/benchmark/organizations — 벤치마크 대상 기관 검색 (Phase 4)

> **대응 화면:** 4.25 벤치마크 분석 — 비교 대상 기관 검색·선택

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `search` | string | N | 기관명 키워드 검색 |
| `category` | string | N | `광역시도`, `기초자치단체`, `공공기관` |
| `limit` | number | N | 최대 결과 수 (기본: 20) |

**허용 역할:** AM, AO

**Response 200:**
```json
{
  "data": [
    {
      "id": "org_ext_busan",
      "name": "부산시",
      "category": "광역시도",
      "platforms": ["youtube", "instagram", "facebook"],
      "isPublicDataOnly": true
    },
    {
      "id": "org_ext_incheon",
      "name": "인천시",
      "category": "광역시도",
      "platforms": ["youtube", "instagram", "naver_blog"],
      "isPublicDataOnly": true
    }
  ]
}
```

---

## 13. 채널 관리 (Channels)

> **대응 화면:** 4.12 채널 관리, 4.23 채널 연동 이력
> **대응 기능:** F12 플랫폼 계정 연동 관리
> **대응 흐름:** 5.4 채널 연동 흐름
> **Phase:** 1-A

### 13.1 GET /channels — 연동 계정 목록

> **대응 화면:** 4.12 연동 계정 탭

**허용 역할:** SA, AM

**Response 200:**
```json
{
  "data": [
    {
      "id": "ch_001",
      "platform": "youtube",
      "accountName": "서울시 공식채널",
      "profileUrl": "https://youtube.com/@seoul_official",
      "status": "ACTIVE",
      "tokenExpiresAt": "2026-09-15T00:00:00Z",
      "tokenStatus": "VALID",
      "connectedAt": "2026-01-10T10:00:00Z",
      "connectedBy": { "name": "김OO" }
    },
    {
      "id": "ch_003",
      "platform": "facebook",
      "accountName": "서울특별시",
      "status": "ACTIVE",
      "tokenExpiresAt": "2026-03-10T00:00:00Z",
      "tokenStatus": "EXPIRING_SOON",
      "connectedAt": "2025-12-20T16:00:00Z"
    }
  ]
}
```

### 13.2 POST /channels/connect/initiate — 채널 연동 시작 (OAuth 리다이렉트 URL 요청)

> **대응 흐름:** 5.4 채널 연동 흐름 — 플랫폼 선택 후

**Request Body:**
```json
{
  "platform": "youtube"
}
```

**Response 200:**
```json
{
  "data": {
    "authUrl": "https://accounts.google.com/o/oauth2/auth?client_id=...&redirect_uri=...&scope=...",
    "state": "oauth_state_token_abc"
  }
}
```

### 13.3 POST /channels/connect/callback — OAuth 콜백 처리

> **대응 흐름:** 5.4 — PubliSync로 콜백

**Request Body:**
```json
{
  "platform": "youtube",
  "code": "authorization_code_from_platform",
  "state": "oauth_state_token_abc"
}
```

**Response 201:**
```json
{
  "data": {
    "id": "ch_006",
    "platform": "youtube",
    "accountName": "서울시 공식채널",
    "profileUrl": "https://youtube.com/@seoul_official",
    "status": "ACTIVE",
    "tokenExpiresAt": "2026-09-15T00:00:00Z",
    "connectedAt": "2026-03-03T10:00:00Z"
  }
}
```

### 13.4 DELETE /channels/:id — 연동 해제

**허용 역할:** SA, AM
**Response:** `204 No Content`

### 13.5 POST /channels/:id/refresh-token — 토큰 수동 갱신

> **대응 화면:** 4.23 [토큰 수동 갱신] 버튼

**Response 200:**
```json
{
  "data": {
    "id": "ch_003",
    "tokenStatus": "VALID",
    "tokenExpiresAt": "2026-09-10T00:00:00Z",
    "refreshedAt": "2026-03-03T10:00:00Z"
  }
}
```

### 13.6 GET /channels/:id/history — 연동 이력

> **대응 화면:** 4.23 채널 연동 이력

**Response 200:**
```json
{
  "data": [
    {
      "type": "TOKEN_REFRESH",
      "actor": { "name": "시스템" },
      "at": "2026-03-01T09:00:00Z",
      "detail": "자동 갱신 완료"
    },
    {
      "type": "TOKEN_REFRESH",
      "actor": { "name": "김OO" },
      "at": "2026-02-15T14:30:00Z",
      "detail": "수동 갱신 완료"
    },
    {
      "type": "CONNECTED",
      "actor": { "name": "김OO" },
      "at": "2026-01-10T10:00:00Z",
      "detail": "OAuth 연동 완료"
    }
  ]
}
```

### 13.7 GET /channels/api-status — API 상태 (Rate Limit 현황)

> **대응 화면:** 4.12 API 상태 탭

**Response 200:**
```json
{
  "data": [
    {
      "platform": "youtube",
      "dailyQuota": 10000,
      "usedToday": 3200,
      "usageRate": 32.0,
      "status": "NORMAL"
    },
    {
      "platform": "instagram",
      "dailyQuota": 5000,
      "usedToday": 850,
      "usageRate": 17.0,
      "status": "NORMAL"
    }
  ]
}
```

---

## 14. 사용자·권한 (Users & Roles)

> **대응 화면:** 4.13 사용자·권한 관리
> **대응 기능:** F08 사용자 및 권한 관리
> **대응 흐름:** 5.5 사용자 초대/가입 흐름
> **Phase:** 1-A

### 14.1 GET /users — 사용자 목록

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `search` | string | N | 이름·이메일 검색 |
| `role` | string | N | `SYSTEM_ADMIN`, `AGENCY_MANAGER`, `AGENCY_OPERATOR`, `CLIENT_DIRECTOR` |
| `status` | string | N | `ACTIVE`, `INACTIVE` |
| `page` | number | N | 기본: 1 |
| `limit` | number | N | 기본: 20 |

**허용 역할:** SA, AM

**Response 200:**
```json
{
  "data": [
    {
      "id": "usr_abc",
      "name": "김OO",
      "email": "kim@agency.co.kr",
      "role": "AGENCY_MANAGER",
      "status": "ACTIVE",
      "organizations": [{ "id": "org_001", "name": "서울시 홍보담당관실" }],
      "lastLoginAt": "2026-03-03T08:30:00Z"
    }
  ],
  "meta": { "total": 15, "page": 1, "limit": 20, "totalPages": 1 }
}
```

### 14.2 POST /users/invite — 사용자 초대

> **대응 화면:** 4.13 [+ 사용자 초대] 버튼
> **대응 흐름:** 5.5 사용자 초대/가입 흐름

**허용 역할:** SA, AM

**Request Body:**
```json
{
  "email": "new_user@seoul.go.kr",
  "role": "CLIENT_DIRECTOR",
  "organizationIds": ["org_001"],
  "message": "PubliSync에 초대합니다."
}
```

**Response 201:**
```json
{
  "data": {
    "inviteId": "inv_001",
    "email": "new_user@seoul.go.kr",
    "role": "CLIENT_DIRECTOR",
    "status": "PENDING",
    "invitedAt": "2026-03-03T10:00:00Z",
    "expiresAt": "2026-03-10T10:00:00Z"
  }
}
```

### 14.3 GET /users/:id — 사용자 상세

> **대응 화면:** 4.13 행 클릭 시 상세 패널

**Response 200:**
```json
{
  "data": {
    "id": "usr_abc",
    "name": "김OO",
    "email": "kim@agency.co.kr",
    "role": "AGENCY_MANAGER",
    "status": "ACTIVE",
    "organizations": [{ "id": "org_001", "name": "서울시 홍보담당관실" }],
    "permissions": ["content.create", "content.edit", "content.publish", "comment.manage", "channel.manage"],
    "createdAt": "2025-06-01T09:00:00Z",
    "lastLoginAt": "2026-03-03T08:30:00Z",
    "recentActivity": [
      { "type": "콘텐츠작성", "target": "정책 브리핑", "at": "2026-03-03T09:15:00Z" },
      { "type": "로그인", "at": "2026-03-03T08:30:00Z" }
    ]
  }
}
```

### 14.4 PUT /users/:id — 사용자 정보 수정

**Request Body:**
```json
{
  "name": "김OO",
  "role": "AGENCY_MANAGER",
  "status": "ACTIVE",
  "organizationIds": ["org_001", "org_002"]
}
```

### 14.5 DELETE /users/:id — 사용자 비활성화

**Response:** `204 No Content` (물리 삭제가 아닌 `INACTIVE` 상태로 전환)

### 14.6 GET /roles — 역할 목록

**Response 200:**
```json
{
  "data": [
    {
      "id": "SYSTEM_ADMIN",
      "name": "시스템 관리자",
      "description": "시스템 전체 관리 권한",
      "permissions": ["*"]
    },
    {
      "id": "AGENCY_MANAGER",
      "name": "수탁업체 관리자",
      "description": "계정 관리·팀원 관리 권한",
      "permissions": ["content.*", "comment.*", "channel.*", "user.manage", "report.*"]
    },
    {
      "id": "AGENCY_OPERATOR",
      "name": "수탁업체 실무자",
      "description": "편집·게시·모니터링 권한",
      "permissions": ["content.create", "content.edit", "content.request_review", "comment.read", "comment.reply"]
    },
    {
      "id": "CLIENT_DIRECTOR",
      "name": "위탁기관 담당자",
      "description": "검수·승인 권한",
      "permissions": ["content.read", "content.approve", "content.reject", "comment.read", "comment.approve_delete", "report.read"]
    }
  ]
}
```

---

## 15. 설정 (Settings)

### 15.1 위탁기관 관리

> **대응 기능:** F08 멀티테넌트 관리
> **Phase:** 1-A

#### GET /organizations — 위탁기관 목록

**허용 역할:** SA, AM

**Response 200:**
```json
{
  "data": [
    {
      "id": "org_001",
      "name": "서울시 홍보담당관실",
      "logoUrl": "/media/org/org_001_logo.png",
      "channelCount": 5,
      "userCount": 4,
      "createdAt": "2025-06-01T09:00:00Z",
      "status": "ACTIVE"
    }
  ]
}
```

#### POST /organizations — 위탁기관 등록

**Request Body:**
```json
{
  "name": "인천시 홍보담당관실",
  "contactEmail": "pr@incheon.go.kr",
  "contactPhone": "032-000-0000"
}
```

#### PUT /organizations/:id — 위탁기관 수정

#### DELETE /organizations/:id — 위탁기관 삭제 (비활성화)

### 15.2 승인 워크플로우 설정

> **대응 화면:** 4.21 승인 워크플로우 설정
> **대응 기능:** F09
> **Phase:** 1-A

#### GET /workflows — 워크플로우 설정 조회

**Response 200:**
```json
{
  "data": {
    "organizationId": "org_001",
    "defaultWorkflow": {
      "steps": [
        { "order": 1, "name": "작성", "type": "AUTHOR" },
        { "order": 2, "name": "검토 요청", "type": "SUBMIT" },
        { "order": 3, "name": "1차 검수", "type": "REVIEW", "reviewerIds": ["usr_jung"] },
        { "order": 4, "name": "승인/반려", "type": "DECISION" },
        { "order": 5, "name": "게시", "type": "PUBLISH" }
      ]
    },
    "fastTrack": {
      "enabled": true,
      "approverIds": ["usr_jung", "usr_choi"],
      "requireReason": true,
      "requirePostReview": true
    },
    "autoRejectConditions": {
      "aiExpressionCheckFailed": false,
      "aiWarningAttachToReviewer": true
    }
  }
}
```

#### PUT /workflows — 워크플로우 설정 저장

**Request Body:** 위와 동일 구조

### 15.3 알림 설정

> **대응 화면:** 4.22 알림 설정 상세
> **대응 기능:** F07, F13
> **Phase:** 1-B

#### GET /notification-settings — 알림 설정 조회

**Response 200:**
```json
{
  "data": {
    "webNotifications": {
      "dangerousComment": true,
      "approvalRequest": true,
      "approvalResult": true,
      "publishComplete": true,
      "publishFailed": true,
      "tokenExpiring": true,
      "systemAnnouncement": true
    },
    "telegram": {
      "enabled": true,
      "botConnected": true,
      "botUsername": "@PubliSync_Bot",
      "channels": [
        {
          "id": "tg_ch_001",
          "name": "위기대응팀 그룹",
          "alertTypes": ["DANGEROUS_COMMENT", "SENTIMENT_SURGE"],
          "active": true
        },
        {
          "id": "tg_ch_002",
          "name": "운영팀 채널",
          "alertTypes": ["PUBLISH_FAILED"],
          "active": true
        }
      ]
    },
    "webPush": {
      "enabled": true,
      "browserPermission": "granted",
      "alertTypes": ["DANGEROUS_COMMENT", "APPROVAL_REQUEST", "PUBLISH_FAILED"]
    }
  }
}
```

#### PUT /notification-settings — 알림 설정 저장

**Request Body:** 위와 동일 구조

#### POST /notification-settings/telegram/test — 텔레그램 테스트 알림 발송

**Request Body:**
```json
{
  "channelId": "tg_ch_001"
}
```

#### POST /notification-settings/telegram/channels — 텔레그램 채널/그룹 추가

**Request Body:**
```json
{
  "name": "관리자 채널",
  "chatId": "-1001234567890",
  "alertTypes": ["SYSTEM_ERROR"]
}
```

---

## 16. 알림 센터 (Notifications)

> **대응 화면:** 4.15 알림 센터 (우측 슬라이드아웃 패널)
> **대응 기능:** F13 알림 센터
> **Phase:** 1-B

### 16.1 GET /notifications — 알림 목록

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `filter` | string | N | `ALL`, `UNREAD` (기본: `ALL`) |
| `type` | string | N | `DANGEROUS_COMMENT`, `APPROVAL_REQUEST`, `APPROVAL_RESULT`, `PUBLISH_COMPLETE`, `PUBLISH_FAILED`, `TOKEN_EXPIRING`, `SYSTEM` |
| `page` | number | N | 기본: 1 |
| `limit` | number | N | 기본: 30 |

**Response 200:**
```json
{
  "data": {
    "unreadCount": 3,
    "notifications": [
      {
        "id": "ntf_001",
        "type": "DANGEROUS_COMMENT",
        "title": "위험 댓글 감지",
        "message": "YouTube · \"이 정책 당장...\"",
        "isRead": false,
        "actionUrl": "/comments/dangerous?id=cmt_501",
        "actionLabel": "대응하기",
        "createdAt": "2026-03-03T09:12:00Z",
        "group": "오늘"
      },
      {
        "id": "ntf_002",
        "type": "APPROVAL_REQUEST",
        "title": "승인 요청",
        "message": "김OO님이 \"정책 브리핑\" 검수를 요청했습니다.",
        "isRead": false,
        "actionUrl": "/approvals/apv_301",
        "actionLabel": "검수하기",
        "createdAt": "2026-03-03T09:00:00Z",
        "group": "오늘"
      },
      {
        "id": "ntf_003",
        "type": "PUBLISH_COMPLETE",
        "title": "게시 완료",
        "message": "\"봄맞이 캠페인\" IG 게시 완료",
        "isRead": true,
        "actionUrl": "/contents/cnt_100",
        "createdAt": "2026-03-03T08:45:00Z",
        "group": "오늘"
      }
    ]
  },
  "meta": { "total": 45, "page": 1, "limit": 30, "totalPages": 2 }
}
```

### 16.2 PATCH /notifications/:id/read — 읽음 처리

**Response 200:** `{ "data": { "id": "ntf_001", "isRead": true } }`

### 16.3 POST /notifications/mark-all-read — 전체 읽음 처리

> **대응 화면:** 4.15 [전체 읽음 처리] 버튼

**Response 200:** `{ "data": { "updatedCount": 3 } }`

### 16.4 GET /notifications/unread-count — 미읽음 알림 수 (경량)

> **대응 화면:** 상단 바 알림 아이콘 뱃지 숫자
> 상단 바 렌더링 시 호출하는 경량 API (전체 알림 목록을 가져오지 않음)

**허용 역할:** SA, AM, AO, CD

**Response 200:**
```json
{
  "data": {
    "unreadCount": 3
  }
}
```

### 16.5 GET /notifications/stream — 실시간 알림 (SSE)

> **대응 화면:** 상단 바, 사이드바 — 실시간 뱃지 갱신, 토스트 알림
> Server-Sent Events(SSE) 방식으로 실시간 알림을 수신

**허용 역할:** SA, AM, AO, CD

**Request:**
```
GET /api/v1/notifications/stream
Accept: text/event-stream
Authorization: Bearer {JWT_ACCESS_TOKEN}
```

**Event 형식:**
```
event: notification
data: {"type":"DANGEROUS_COMMENT","title":"위험 댓글 감지","message":"YouTube · \"이 정책 당장...\"","actionUrl":"/comments/dangerous?id=cmt_501"}

event: badge-update
data: {"unreadNotifications":4,"pendingApprovals":3,"dangerousComments":6}
```

> - 연결 유지: 30초마다 `event: ping` 전송
> - 재연결: 클라이언트는 `Last-Event-ID` 헤더로 누락 이벤트 복구
> - Fallback: SSE 연결 불가 시 16.4 폴링 (30초 간격)

---

## 17. 감사 로그 (Audit Logs)

> **대응 화면:** 4.14 감사 로그
> **대응 기능:** F14 활동 이력 관리
> **Phase:** 1-B

### 17.1 GET /audit-logs — 감사 로그 조회

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `startDate` | string | N | 시작일 |
| `endDate` | string | N | 종료일 |
| `actorId` | string | N | 행위자 ID |
| `actionType` | string | N | `CONTENT_CREATE`, `CONTENT_EDIT`, `CONTENT_DELETE`, `CONTENT_PUBLISH`, `COMMENT_DELETE`, `COMMENT_HIDE`, `COMMENT_REPLY`, `APPROVAL_APPROVE`, `APPROVAL_REJECT`, `CHANNEL_CONNECT`, `CHANNEL_DISCONNECT`, `USER_LOGIN`, `USER_ROLE_CHANGE` 등 |
| `targetSearch` | string | N | 대상 키워드 검색 |
| `page` | number | N | 기본: 1 |
| `limit` | number | N | 기본: 50 |

**허용 역할:** SA, AM, CD (CD는 본인 기관만)

**Response 200:**
```json
{
  "data": [
    {
      "id": "log_001",
      "actionType": "CONTENT_CREATE",
      "actionLabel": "콘텐츠작성",
      "actor": { "id": "usr_abc", "name": "김OO" },
      "target": { "type": "content", "id": "cnt_201", "label": "정책브리핑" },
      "at": "2026-03-03T09:15:23Z",
      "hasDetail": true
    }
  ],
  "meta": { "total": 1250, "page": 1, "limit": 50, "totalPages": 25 }
}
```

### 17.2 GET /audit-logs/:id — 로그 상세

> **대응 화면:** 4.14 [보기] 클릭 시

**Response 200:**
```json
{
  "data": {
    "id": "log_001",
    "actionType": "CONTENT_CREATE",
    "actor": { "id": "usr_abc", "name": "김OO", "email": "kim@agency.co.kr" },
    "target": { "type": "content", "id": "cnt_201", "label": "서울시 정책 브리핑 3월호" },
    "at": "2026-03-03T09:15:23Z",
    "ipAddress": "203.0.113.42",
    "userAgent": "Chrome/120.0",
    "changes": {
      "title": { "before": null, "after": "서울시 정책 브리핑 3월호" },
      "status": { "before": null, "after": "DRAFT" }
    },
    "context": {
      "organizationId": "org_001",
      "sessionId": "sess_abc123"
    }
  }
}
```

### 17.3 GET /audit-logs/export — 로그 내보내기

> **대응 화면:** 4.14 [CSV 내보내기] [PDF] 버튼

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `format` | string | Y | `csv`, `pdf` |
| `startDate` | string | Y | 시작일 |
| `endDate` | string | Y | 종료일 |
| (기타 필터) | | | 17.1과 동일 |

**Response:** `Content-Type: text/csv` 또는 `application/pdf` 바이너리 스트림

---

## 18. AI 기능 (AI)

> **대응 기능:** F02, F03, F05, F15, F17, F20, F21, F22
> **공통 정책:** Human-in-the-Loop (AI 결과는 항상 "제안", 최종 결정은 사람)

모든 AI 엔드포인트는 비동기 처리될 수 있으며, 실패 시 수동 대체 경로(Fallback)를 안내합니다.

**공통 AI 응답 래퍼:**
```json
{
  "data": {
    "result": { ... },
    "isAiGenerated": true,
    "confidence": 0.85,
    "fallbackAvailable": true,
    "fallbackMessage": "AI 결과가 만족스럽지 않으면 직접 입력하세요."
  }
}
```

### 18.1 POST /ai/generate-title — AI 제목 생성 (Phase 1-B)

> **대응 화면:** 4.2 [🤖 AI 제목 생성] 버튼

**Request Body:**
```json
{
  "body": "서울시 3월 주요 정책을 안내합니다...",
  "platforms": ["youtube", "instagram"],
  "mediaIds": ["med_001"]
}
```

**Response 200:**
```json
{
  "data": {
    "suggestions": [
      { "text": "서울시 3월 정책 브리핑 — 핵심 5가지", "platform": "youtube" },
      { "text": "3분 만에 보는 서울시 3월 정책 변화", "platform": "youtube" },
      { "text": "서울시가 알려주는 3월 새 소식", "platform": "instagram" }
    ],
    "isAiGenerated": true
  }
}
```

### 18.2 POST /ai/generate-description — AI 설명문 생성 (Phase 1-B)

> **대응 화면:** 4.2 [🤖 AI 설명문 생성] 버튼

**Request Body:**
```json
{
  "title": "서울시 정책 브리핑 3월호",
  "body": "...",
  "platform": "youtube"
}
```

**Response 200:**
```json
{
  "data": {
    "description": "서울시의 3월 주요 정책을 한눈에 정리했습니다. 교통, 환경, 복지 분야의 핵심 변화를 확인하세요.",
    "isAiGenerated": true
  }
}
```

### 18.3 POST /ai/generate-hashtags — AI 해시태그 추천 (Phase 1-B)

> **대응 화면:** 4.2 [🤖 AI 해시태그 추천] 버튼

**Request Body:**
```json
{
  "title": "서울시 정책 브리핑 3월호",
  "body": "...",
  "platform": "instagram"
}
```

**Response 200:**
```json
{
  "data": {
    "hashtags": ["#서울시", "#정책브리핑", "#3월정책", "#서울시정", "#시민소통"],
    "isAiGenerated": true
  }
}
```

### 18.4 POST /ai/tone-transform — 플랫폼별 톤앤매너 변환 (Phase 2)

> **대응 화면:** 4.2 [🤖 플랫폼별 톤 변환] 버튼
> **대응 기능:** F17

**Request Body:**
```json
{
  "originalText": "서울시는 3월부터 대중교통 요금 체계를 개편합니다...",
  "platforms": ["youtube", "instagram", "x", "naver_blog"]
}
```

**Response 200:**
```json
{
  "data": {
    "transformations": {
      "youtube": { "text": "서울시 대중교통 요금이 바뀝니다! 3월부터 달라지는 요금 체계를 자세히 알아보세요.", "tone": "정보 전달형" },
      "instagram": { "text": "3월부터 달라지는 서울 대중교통 🚌\n요금 체계 개편 소식, 한눈에 확인하세요 ✨", "tone": "감성·시각 중심" },
      "x": { "text": "서울시 3월 대중교통 요금 체계 개편 — 달라지는 핵심 포인트 정리 🚇", "tone": "핵심 압축형" },
      "naver_blog": { "text": "안녕하세요, 서울시입니다. 2026년 3월부터 대중교통 요금 체계가 개편됩니다. 이번 포스팅에서는...", "tone": "상세 서술형" }
    },
    "isAiGenerated": true
  }
}
```

### 18.5 POST /ai/content-review — 표현 가이드 자동 검수 (Phase 2)

> **대응 화면:** 4.2 AI 검수 결과 패널, [🤖 AI 재검수] 버튼
> **대응 기능:** F21

**Request Body:**
```json
{
  "title": "서울시 정책 브리핑 3월호",
  "body": "...",
  "mediaIds": ["med_001", "med_002"]
}
```

**Response 200:**
```json
{
  "data": {
    "results": [
      { "category": "expression", "status": "PASS", "message": "부적절 표현 없음", "details": [] },
      { "category": "privacy", "status": "PASS", "message": "개인정보 미검출", "details": [] },
      {
        "category": "accessibility",
        "status": "WARNING",
        "message": "대체텍스트 미입력 (이미지 2건)",
        "details": [
          { "mediaId": "med_002", "issue": "이미지 alt 텍스트 미입력" }
        ]
      },
      { "category": "copyright", "status": "PASS", "message": "저작권 이상 없음", "details": [] }
    ],
    "overallStatus": "WARNING",
    "isAiGenerated": true
  }
}
```

### 18.6 POST /ai/generate-reply — AI 답글 생성 (Phase 2)

> **대응 화면:** 4.6 [🤖 AI 답글 생성] 버튼
> **대응 기능:** F05

**Request Body:**
```json
{
  "commentId": "cmt_501",
  "commentText": "이 정책 당장 철회해라 담당자 나와",
  "platform": "youtube",
  "contentTitle": "서울시 정책 브리핑",
  "templateId": null
}
```

**Response 200:**
```json
{
  "data": {
    "replyText": "안녕하세요, 서울시입니다. 해당 정책에 대한 시민 여러분의 의견을 소중히 듣고 있습니다. 보다 자세한 사항은 서울시 홍보담당관실(02-XXX-XXXX)로 문의해 주시면 성실히 답변드리겠습니다.",
    "usedTemplateId": "tpl_101",
    "isAiGenerated": true,
    "confidence": 0.88
  }
}
```

### 18.7 POST /ai/generate-subtitles — AI 자막 생성 (Phase 2)

> **대응 화면:** 4.18 AI 영상 편집 보조 — 자막 편집기
> **대응 기능:** F03

**Request Body:**
```json
{
  "mediaId": "med_001",
  "language": "ko"
}
```

**Response 202:**
```json
{
  "data": {
    "jobId": "job_stt_001",
    "status": "PROCESSING",
    "estimatedSeconds": 60,
    "message": "자막을 생성 중입니다..."
  }
}
```

**완료 후 GET /ai/jobs/:jobId:**
```json
{
  "data": {
    "status": "COMPLETED",
    "subtitles": [
      { "index": 1, "startTime": "00:00:00", "endTime": "00:00:05", "text": "안녕하세요 서울시 정책 브리핑입니다" },
      { "index": 2, "startTime": "00:00:05", "endTime": "00:00:10", "text": "오늘은 3월 교통 정책에 대해..." }
    ],
    "totalSegments": 45,
    "isAiGenerated": true
  }
}
```

### 18.8 POST /ai/suggest-effects — AI 효과음·이모지 추천 (Phase 2)

> **대응 화면:** 4.18 AI 추천 패널
> **대응 기능:** F03

**Request Body:**
```json
{
  "mediaId": "med_001"
}
```

**Response 200:**
```json
{
  "data": {
    "soundEffects": [
      { "timestamp": "00:00:00", "type": "intro", "name": "인트로 효과음", "previewUrl": "/audio/intro.mp3" },
      { "timestamp": "00:02:30", "type": "transition", "name": "전환 효과음", "previewUrl": "/audio/transition.mp3" }
    ],
    "emojis": [
      { "timestamp": "00:00:15", "emoji": "😊", "reason": "밝은 인사" },
      { "timestamp": "00:05:20", "emoji": "📊", "reason": "통계 설명" }
    ],
    "isAiGenerated": true,
    "disclaimer": "AI 추천은 PoC 검증 후 가용 범위가 결정됩니다."
  }
}
```

### 18.9 POST /ai/extract-shortform — AI 숏폼 구간 추출 (Phase 2)

> **대응 화면:** 4.19 AI 숏폼 편집 화면
> **대응 기능:** F15

**Request Body:**
```json
{
  "mediaId": "med_001",
  "maxDuration": 60,
  "count": 3
}
```

**Response 200:**
```json
{
  "data": {
    "candidates": [
      {
        "index": 1,
        "startTime": "00:00:30",
        "endTime": "00:01:15",
        "duration": 45,
        "description": "핵심 정책 요약 부분",
        "confidence": "HIGH",
        "thumbnailUrl": "/media/preview/shortform_1.jpg"
      },
      {
        "index": 2,
        "startTime": "00:04:20",
        "endTime": "00:05:30",
        "duration": 70,
        "description": "시민 인터뷰 하이라이트",
        "confidence": "MODERATE",
        "thumbnailUrl": "/media/preview/shortform_2.jpg"
      }
    ],
    "isAiGenerated": true
  }
}
```

### 18.10 POST /ai/optimal-time — 최적 게시 시간 추천 (Phase 3)

> **대응 화면:** 4.2 [🤖 최적 시간 추천] 버튼
> **대응 기능:** F20

**Request Body:**
```json
{
  "contentId": "cnt_201",
  "platforms": ["youtube", "instagram"]
}
```

**Response 200:**
```json
{
  "data": {
    "recommendations": [
      { "platform": "youtube", "dayOfWeek": "TUE", "time": "09:00", "reason": "유사 콘텐츠 평균 조회수 최고 시간대" },
      { "platform": "instagram", "dayOfWeek": "THU", "time": "12:00", "reason": "타겟 오디언스 활성 시간대" }
    ],
    "isAiGenerated": true,
    "isBeta": true
  }
}
```

### 18.11 POST /ai/generate-thumbnail — AI 썸네일 생성 (Phase 4)

> **대응 기능:** F16

**Request Body:**
```json
{
  "mediaId": "med_001",
  "titleOverlay": "서울시 3월 정책",
  "aspectRatios": ["16:9", "1:1", "9:16"]
}
```

**Response 200:**
```json
{
  "data": {
    "candidates": [
      {
        "index": 1,
        "frameTimestamp": "00:01:23",
        "thumbnails": {
          "16:9": { "url": "/media/thumbnails/gen_1_16x9.jpg" },
          "1:1": { "url": "/media/thumbnails/gen_1_1x1.jpg" },
          "9:16": { "url": "/media/thumbnails/gen_1_9x16.jpg" }
        }
      }
    ],
    "isAiGenerated": true
  }
}
```

### 18.12 POST /ai/translate — 다국어 번역 (Phase 4)

> **대응 기능:** F22

**Request Body:**
```json
{
  "text": "서울시 3월 정책 브리핑입니다...",
  "targetLanguages": ["en", "zh-CN", "ja", "vi"]
}
```

**Response 200:**
```json
{
  "data": {
    "translations": {
      "en": "This is the Seoul Metropolitan Government March policy briefing...",
      "zh-CN": "这是首尔市三月政策简报...",
      "ja": "ソウル市3月の政策ブリーフィングです...",
      "vi": "Đây là bản tin chính sách tháng 3 của Thành phố Seoul..."
    },
    "isAiGenerated": true
  }
}
```

### 18.13 POST /ai/improve-template — 템플릿 개선 제안 (Phase 2)

> **대응 화면:** 4.20 [🤖 AI로 개선 제안 받기] 버튼

**Request Body:**
```json
{
  "templateId": "tpl_101",
  "currentContent": "안녕하세요, {기관명}입니다. 불편을 드려 죄송합니다..."
}
```

**Response 200:**
```json
{
  "data": {
    "improvedContent": "안녕하세요, {기관명}입니다. 소중한 의견 감사드립니다. 말씀해 주신 불편 사항은 {담당부서}에서 확인 후 신속하게 개선하겠습니다. 추가 문의는 {연락처}로 연락 부탁드립니다.",
    "changeHighlights": ["감사 표현 추가", "개선 의지 표현 강화", "담당부서 변수 활용"],
    "isAiGenerated": true
  }
}
```

### 18.14 GET /ai/jobs/:jobId — AI 작업 상태 조회 (공통)

> 비동기 AI 작업의 진행 상태를 폴링

**Response 200:**
```json
{
  "data": {
    "jobId": "job_stt_001",
    "type": "SUBTITLE_GENERATION",
    "status": "PROCESSING",
    "progress": 65,
    "estimatedRemainingSeconds": 20
  }
}
```

> `status` 값: `QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`

---

## 19. 글로벌 검색 (Search)

> **대응 화면:** 상단 바 글로벌 검색
> **Phase:** 1-A (기본), Phase별 검색 대상 확장

### 19.1 GET /search — 통합 검색

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `q` | string | Y | 검색 키워드 |
| `type` | string | N | `ALL`, `CONTENT`, `COMMENT`, `MEDIA`, `USER`, `AUDIT_LOG` (기본: `ALL`) |
| `limit` | number | N | 유형별 최대 결과 수 (기본: 5) |

**Response 200:**
```json
{
  "data": {
    "contents": [
      { "id": "cnt_201", "title": "서울시 정책 브리핑 3월호", "status": "PENDING_REVIEW", "matchField": "title" }
    ],
    "comments": [
      { "id": "cmt_501", "text": "이 정책 당장 철회...", "platform": "youtube", "matchField": "text" }
    ],
    "media": [
      { "id": "med_001", "fileName": "정책브리핑.mp4", "type": "video", "matchField": "fileName" }
    ],
    "users": [
      { "id": "usr_abc", "name": "김OO", "role": "AGENCY_MANAGER", "matchField": "name" }
    ],
    "auditLogs": []
  }
}
```

---

## 20. 시스템 관리 (Admin)

> **대응 화면:** 부록 — 시스템 관리자 전용 화면
> **허용 역할:** SA 전용
> **Phase:** 1-A

### 20.1 GET /admin/agencies — 수탁업체 관리

**Response 200:**
```json
{
  "data": [
    {
      "id": "agency_001",
      "name": "OO미디어",
      "organizationCount": 3,
      "userCount": 8,
      "status": "ACTIVE",
      "createdAt": "2025-06-01T09:00:00Z"
    }
  ]
}
```

### 20.2 POST /admin/agencies — 수탁업체 등록

### 20.3 GET /admin/ai-usage — AI 사용량 모니터링

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `period` | string | N | `7d`, `30d`, `90d` |
| `organizationId` | string | N | 기관별 필터 |

**Response 200:**
```json
{
  "data": {
    "totalCalls": 12500,
    "totalCost": 45.20,
    "byFeature": [
      { "feature": "TITLE_GENERATION", "calls": 3200, "cost": 8.50 },
      { "feature": "DESCRIPTION_GENERATION", "calls": 2800, "cost": 7.20 },
      { "feature": "SENTIMENT_ANALYSIS", "calls": 4500, "cost": 15.00 },
      { "feature": "SUBTITLE_GENERATION", "calls": 120, "cost": 12.50 }
    ],
    "byOrganization": [
      { "id": "org_001", "name": "서울시", "calls": 5200, "cost": 18.50 },
      { "id": "org_002", "name": "부산시", "calls": 3800, "cost": 14.20 }
    ],
    "trend": {
      "labels": ["2026-02-01", "2026-02-08"],
      "calls": [2800, 3200],
      "cost": [10.50, 12.30]
    }
  }
}
```

### 20.4 GET /admin/rate-limits — 플랫폼 API Rate Limit 현황

**Response 200:**
```json
{
  "data": [
    {
      "platform": "youtube",
      "dailyQuota": 10000,
      "usedToday": 3200,
      "usageRate": 32.0,
      "status": "NORMAL",
      "threshold": 80,
      "backpressureActive": false,
      "history": [
        { "date": "2026-03-02", "usageRate": 28.5 },
        { "date": "2026-03-01", "usageRate": 35.2 }
      ]
    }
  ]
}
```

### 20.5 GET /admin/health — 시스템 헬스 체크

**Response 200:**
```json
{
  "data": {
    "status": "HEALTHY",
    "services": {
      "api": { "status": "UP", "responseTime": 45 },
      "database": { "status": "UP", "responseTime": 12 },
      "redis": { "status": "UP", "responseTime": 3 },
      "aiService": { "status": "UP", "responseTime": 850 },
      "fileStorage": { "status": "UP", "usedSpace": "12.3GB", "totalSpace": "500GB" },
      "jobQueue": { "status": "UP", "pendingJobs": 3, "failedJobs": 0 }
    },
    "uptime": "15d 6h 23m",
    "version": "1.0.0"
  }
}
```

### 20.6 GET /admin/announcements — 시스템 공지 목록

### 20.7 POST /admin/announcements — 시스템 공지 등록

**Request Body:**
```json
{
  "title": "시스템 점검 안내",
  "content": "2026-03-10 02:00~06:00 시스템 정기 점검이 진행됩니다.",
  "type": "MAINTENANCE",
  "publishAt": "2026-03-08T09:00:00Z"
}
```

---

## 21. 부록: API 엔드포인트 전체 요약

### 21.1 Phase별 엔드포인트 매핑

#### Phase 1-A — 최소 MVP (총 56개)

| # | Method | Endpoint | 도메인 | 대응 화면 | 대응 기능 |
|:---:|---|---|---|---|---|
| 1 | POST | /auth/login | 인증 | 4.16 | F08 |
| 2 | POST | /auth/refresh | 인증 | — | F08 |
| 3 | POST | /auth/logout | 인증 | — | F08 |
| 4 | POST | /auth/password/reset-request | 인증 | 4.16 | F08 |
| 5 | POST | /auth/password/reset | 인증 | 4.16 | F08 |
| 6 | POST | /auth/invite/accept | 인증 | 4.16 | F08 |
| 7 | GET | /auth/invite/verify | 인증 | 4.16 | F08 |
| 8 | GET | /workspaces | 워크스페이스 | 상단 바 | — |
| 9 | GET | /users/me | 워크스페이스 | 상단 바 | — |
| 10 | GET | /dashboard/summary | 대시보드 | 4.1 | F06 |
| 11 | GET | /dashboard/platform-trends | 대시보드 | 4.1 | F06 |
| 12 | GET | /dashboard/approval-status | 대시보드 | 4.1 | F09 |
| 13 | GET | /dashboard/recent-contents | 대시보드 | 4.1 | F01 |
| 14 | GET | /dashboard/today-schedule | 대시보드 | 4.1 | F01 |
| 15 | GET | /dashboard/all-organizations | 대시보드 | 4.1 | F06 |
| 16 | GET | /dashboard/badge-counts | 대시보드 | 사이드바 | — |
| 17 | POST | /contents | 콘텐츠 | 4.2 | F01 |
| 18 | GET | /contents | 콘텐츠 | 4.3 | F01 |
| 19 | GET | /contents/:id | 콘텐츠 | 4.2, 4.3 | F01 |
| 20 | PUT | /contents/:id | 콘텐츠 | 4.2 | F01 |
| 21 | DELETE | /contents/:id | 콘텐츠 | 4.3 | F01 |
| 22 | POST | /contents/:id/save-draft | 콘텐츠 | 4.2 | F01 |
| 23 | POST | /contents/:id/request-review | 콘텐츠 | 4.2 | F09 |
| 24 | GET | /contents/:id/publish-history | 콘텐츠 | 4.17 | F01 |
| 25 | POST | /contents/:id/retry-publish | 콘텐츠 | 4.17 | F01 |
| 26 | POST | /contents/bulk-action | 콘텐츠 | 4.3 | F01 |
| 27 | POST | /contents/:id/cancel-publish | 콘텐츠 | 4.17 | F01 |
| 28 | GET | /approvals | 승인 | 4.4 | F09 |
| 29 | GET | /approvals/:id | 승인 | 4.4 | F09 |
| 30 | POST | /approvals/:id/approve | 승인 | 4.4 | F09 |
| 31 | POST | /approvals/:id/reject | 승인 | 4.4 | F09 |
| 32 | GET | /channels | 채널 | 4.12 | F12 |
| 33 | POST | /channels/connect/initiate | 채널 | 4.12 | F12 |
| 34 | POST | /channels/connect/callback | 채널 | — | F12 |
| 35 | DELETE | /channels/:id | 채널 | 4.12 | F12 |
| 36 | POST | /channels/:id/refresh-token | 채널 | 4.23 | F12 |
| 37 | GET | /channels/:id/history | 채널 | 4.23 | F12 |
| 38 | GET | /channels/api-status | 채널 | 4.12 | F12 |
| 39 | GET | /users | 사용자 | 4.13 | F08 |
| 40 | POST | /users/invite | 사용자 | 4.13 | F08 |
| 41 | GET | /users/:id | 사용자 | 4.13 | F08 |
| 42 | PUT | /users/:id | 사용자 | 4.13 | F08 |
| 43 | DELETE | /users/:id | 사용자 | 4.13 | F08 |
| 44 | GET | /roles | 사용자 | 4.13 | F08 |
| 45 | GET | /organizations | 설정 | — | F08 |
| 46 | POST | /organizations | 설정 | — | F08 |
| 47 | PUT | /organizations/:id | 설정 | — | F08 |
| 48 | DELETE | /organizations/:id | 설정 | — | F08 |
| 49 | GET | /workflows | 설정 | 4.21 | F09 |
| 50 | PUT | /workflows | 설정 | 4.21 | F09 |
| 51 | GET | /search | 검색 | 상단 바 | — |
| 52 | GET | /admin/agencies | 시스템 | — | — |
| 53 | POST | /admin/agencies | 시스템 | — | — |
| 54 | GET | /admin/health | 시스템 | — | — |
| 55 | GET | /admin/announcements | 시스템 | — | — |
| 56 | POST | /admin/announcements | 시스템 | — | — |

#### Phase 1-B — MVP 확장 (추가 33개)

| # | Method | Endpoint | 도메인 | 대응 화면 | 대응 기능 |
|:---:|---|---|---|---|---|
| 57 | GET | /dashboard/sentiment-summary | 대시보드 | 4.1 | F06 |
| 58 | GET | /comments | 댓글 | 4.6 | F04 |
| 59 | GET | /comments/:id | 댓글 | 4.6 | F04 |
| 60 | GET | /comments/dangerous | 댓글 | 4.7 | F04 |
| 61 | POST | /comments/:id/reply | 댓글 | 4.6 | F04 |
| 62 | POST | /comments/:id/hide | 댓글 | 4.7 | F04 |
| 63 | POST | /comments/:id/delete-request | 댓글 | 4.7 | F04 |
| 64 | POST | /comments/:id/ignore | 댓글 | 4.7 | F04 |
| 65 | POST | /comments/:id/delete-approve | 댓글 | 4.7 | F04 |
| 66 | GET | /reply-templates | 템플릿 | 4.20 | F05 |
| 67 | POST | /reply-templates | 템플릿 | 4.20 | F05 |
| 68 | PUT | /reply-templates/:id | 템플릿 | 4.20 | F05 |
| 69 | DELETE | /reply-templates/:id | 템플릿 | 4.20 | F05 |
| 70 | GET | /analytics/performance | 분석 | 4.9 | F06 |
| 71 | GET | /analytics/engagement-heatmap | 분석 | 4.9 | F06 |
| 72 | GET | /analytics/performance/export | 분석 | 4.9 | F06 |
| 73 | GET | /notifications | 알림 | 4.15 | F13 |
| 74 | PATCH | /notifications/:id/read | 알림 | 4.15 | F13 |
| 75 | POST | /notifications/mark-all-read | 알림 | 4.15 | F13 |
| 76 | GET | /notifications/unread-count | 알림 | 상단 바 | F13 |
| 77 | GET | /notifications/stream | 알림 | 상단 바 | F13 |
| 78 | GET | /notification-settings | 설정 | 4.22 | F07, F13 |
| 79 | PUT | /notification-settings | 설정 | 4.22 | F07, F13 |
| 80 | POST | /notification-settings/telegram/test | 설정 | 4.22 | F07 |
| 81 | POST | /notification-settings/telegram/channels | 설정 | 4.22 | F07 |
| 82 | GET | /audit-logs | 감사 | 4.14 | F14 |
| 83 | GET | /audit-logs/:id | 감사 | 4.14 | F14 |
| 84 | GET | /audit-logs/export | 감사 | 4.14 | F14 |
| 85 | POST | /ai/generate-title | AI | 4.2 | F02 |
| 86 | POST | /ai/generate-description | AI | 4.2 | F02 |
| 87 | POST | /ai/generate-hashtags | AI | 4.2 | F02 |
| 88 | GET | /admin/ai-usage | 시스템 | — | — |
| 89 | GET | /admin/rate-limits | 시스템 | — | F12 |

#### Phase 2 — AI 콘텐츠 고도화 (추가 20개)

| # | Method | Endpoint | 도메인 | 대응 화면 | 대응 기능 |
|:---:|---|---|---|---|---|
| 90 | GET | /calendar/events | 캘린더 | 4.5 | F10 |
| 91 | PATCH | /calendar/events/:id/reschedule | 캘린더 | 4.5 | F10 |
| 92 | GET | /calendar/holidays | 캘린더 | 4.5 | F10 |
| 93 | PUT | /calendar/holidays | 캘린더 | 4.5 | F10 |
| 94 | GET | /media | 미디어 | 4.8 | F11 |
| 95 | POST | /media/upload | 미디어 | 4.8 | F11 |
| 96 | GET | /media/:id | 미디어 | 4.8 | F11 |
| 97 | PUT | /media/:id | 미디어 | 4.8 | F11 |
| 98 | DELETE | /media/:id | 미디어 | 4.8 | F11 |
| 99 | GET | /media/folders | 미디어 | 4.8 | F11 |
| 100 | POST | /media/folders | 미디어 | 4.8 | F11 |
| 101 | POST | /media/shortform | 미디어 | 4.19 | F15 |
| 102 | POST | /ai/tone-transform | AI | 4.2 | F17 |
| 103 | POST | /ai/content-review | AI | 4.2 | F21 |
| 104 | POST | /ai/generate-reply | AI | 4.6 | F05 |
| 105 | POST | /ai/generate-subtitles | AI | 4.18 | F03 |
| 106 | POST | /ai/suggest-effects | AI | 4.18 | F03 |
| 107 | POST | /ai/extract-shortform | AI | 4.19 | F15 |
| 108 | POST | /ai/improve-template | AI | 4.20 | F05 |
| 109 | GET | /ai/jobs/:jobId | AI | — | 공통 |

#### Phase 3 — 분석·보고 고도화 (추가 9개)

| # | Method | Endpoint | 도메인 | 대응 화면 | 대응 기능 |
|:---:|---|---|---|---|---|
| 110 | GET | /analytics/sentiment-trend | 분석 | 4.11 | F18 |
| 111 | GET | /reports | 리포트 | 4.10 | F19 |
| 112 | POST | /reports/generate | 리포트 | 4.10 | F19 |
| 113 | GET | /reports/:id | 리포트 | 4.10 | F19 |
| 114 | PUT | /reports/:id | 리포트 | 4.10 | F19 |
| 115 | POST | /reports/:id/finalize | 리포트 | 4.10 | F19 |
| 116 | GET | /reports/:id/download | 리포트 | 4.10 | F19 |
| 117 | GET | /analytics/prediction | 분석 | 4.24 | F20 |
| 118 | POST | /ai/optimal-time | AI | 4.2 | F20 |

#### Phase 4 — 확장 기능 (추가 4개)

| # | Method | Endpoint | 도메인 | 대응 화면 | 대응 기능 |
|:---:|---|---|---|---|---|
| 119 | GET | /analytics/benchmark | 분석 | 4.25 | F23 |
| 120 | GET | /analytics/benchmark/organizations | 분석 | 4.25 | F23 |
| 121 | POST | /ai/generate-thumbnail | AI | 4.2 | F16 |
| 122 | POST | /ai/translate | AI | 4.2 | F22 |

### 21.2 도메인별 엔드포인트 수 요약

| 도메인 | 엔드포인트 수 | Phase |
|---|:---:|---|
| 인증 (Auth) | 7 | 1-A |
| 워크스페이스 (Workspaces) | 2 | 1-A |
| 대시보드 (Dashboard) | 8 | 1-A, 1-B |
| 콘텐츠 (Contents) | 11 | 1-A |
| 승인 (Approvals) | 4 | 1-A |
| 캘린더 (Calendar) | 4 | 2 |
| 댓글 (Comments) | 8 | 1-B |
| 답글 템플릿 (Reply Templates) | 4 | 1-B |
| 미디어 (Media) | 8 | 2 |
| 분석·리포트 (Analytics & Reports) | 13 | 1-B, 3, 4 |
| 채널 (Channels) | 7 | 1-A |
| 사용자·권한 (Users & Roles) | 6 | 1-A |
| 설정 (Settings) | 10 | 1-A, 1-B |
| 알림 (Notifications) | 5 | 1-B |
| 감사 로그 (Audit Logs) | 3 | 1-B |
| AI 기능 (AI) | 14 | 1-B, 2, 3, 4 |
| 검색 (Search) | 1 | 1-A |
| 시스템 관리 (Admin) | 7 | 1-A, 1-B |
| **합계** | **122** | |

### 21.3 화면 → API 매핑 요약

| # | 화면 | 사용 API |
|:---:|---|---|
| 1 | 4.16 로그인/인증 | 3.1~3.7 |
| 2 | 상단 바 + 사이드바 | 4.1, 4.2, 5.8, 16.1, 16.4, 16.5, 19.1 |
| 3 | 4.1 대시보드 | 5.1~5.8 |
| 4 | 4.2 새 콘텐츠 작성 | 6.1, 6.3, 6.4, 6.6, 6.7, 18.1~18.5, 18.10, 18.11, 18.12 |
| 5 | 4.3 콘텐츠 목록 | 6.2, 6.3, 6.5, 6.10 |
| 6 | 4.4 승인 대기 + 검수 | 7.1~7.4 |
| 7 | 4.5 캘린더 | 8.1~8.4 |
| 8 | 4.6 통합 댓글함 | 9.1, 9.2, 9.4, 18.6 |
| 9 | 4.7 위험 댓글 | 9.3, 9.5~9.8, 18.6 |
| 10 | 4.8 미디어 라이브러리 | 11.1~11.7 |
| 11 | 4.9 성과 분석 | 12.1, 12.2, 12.12 |
| 12 | 4.10 운영 리포트 | 12.4~12.9 |
| 13 | 4.11 여론 동향 | 12.3 |
| 14 | 4.12 채널 관리 | 13.1~13.4, 13.7 |
| 15 | 4.13 사용자·권한 | 14.1~14.6 |
| 16 | 4.14 감사 로그 | 17.1~17.3 |
| 17 | 4.15 알림 센터 | 16.1~16.5 |
| 18 | 4.17 게시 이력/실패 | 6.8, 6.9, 6.11 |
| 19 | 4.18 AI 자막 편집기 | 18.7, 18.8, 18.14 |
| 20 | 4.19 AI 숏폼 편집 | 18.9, 11.8, 18.14 |
| 21 | 4.20 답글 템플릿 | 10.1~10.4, 18.13 |
| 22 | 4.21 승인 워크플로우 설정 | 15.2 (GET/PUT /workflows) |
| 23 | 4.22 알림 설정 | 15.3 (GET/PUT /notification-settings, 텔레그램) |
| 24 | 4.23 채널 연동 이력 | 13.5, 13.6 |
| 25 | 4.24 성과 예측 | 12.10 |
| 26 | 4.25 벤치마크 분석 | 12.11, 12.13 |

---

> **본 문서는 화면 설계서 v1.2 기반의 API v1.1이며, 기술 아키텍처 설계 및 데이터베이스 설계 단계에서 구체화한다.**
> 각 엔드포인트의 상세 에러 케이스, 요청/응답 검증 규칙, Rate Limit 정책은 상세 설계 시 보완한다.
