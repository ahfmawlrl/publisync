# PubliSync API 빠른 참조

> 122개 엔드포인트 한 줄 참조. 상세 스펙은 `docs/API_설계서.md` 참조.

---

## 공통 규격

### 응답 구조

```json
{
  "success": true,
  "data": { ... },
  "meta": { "timestamp": "2026-03-03T09:00:00Z" }
}
```

### 목록 응답 (페이지네이션)

```json
{
  "success": true,
  "data": [ ... ],
  "meta": { "total": 237, "page": 1, "limit": 20, "totalPages": 12, "timestamp": "..." }
}
```

### AI 응답 래퍼

```json
{
  "isAiGenerated": true,
  "confidence": 0.85,
  "fallbackAvailable": true,
  "model": "gpt-4o-mini",
  "suggestions": [{ "content": "...", "score": 0.85 }],
  "usage": { "promptTokens": 150, "completionTokens": 50, "totalTokens": 200, "estimatedCost": 0.0003 }
}
```

### 에러 응답

```json
{
  "success": false,
  "error": { "code": "VALIDATION_ERROR", "message": "제목은 필수 입력 항목입니다.", "details": [...] },
  "meta": { "timestamp": "..." }
}
```

### 인증 헤더

```
Authorization: Bearer {JWT_ACCESS_TOKEN}
X-Workspace-Id: {organization_id}
X-Request-Id: {uuid-v4}
```

### HTTP 상태 코드

| 코드 | 의미 | 코드 | 의미 |
|---|---|---|---|
| 200 | 성공 | 404 | 리소스 없음 |
| 201 | 생성 성공 | 409 | 충돌 (중복/상태 충돌) |
| 204 | 성공 (본문 없음) | 423 | 계정 잠금 |
| 400 | 잘못된 요청 | 429 | Rate Limit 초과 |
| 401 | 인증 실패 | 500 | 서버 오류 |
| 403 | 권한 없음 | 502 | 외부 서비스 오류 |

### 역할 약어

| SA | AM | AO | CD |
|---|---|---|---|
| 시스템 관리자 | 수탁업체 관리자 | 수탁업체 실무자 | 위탁기관 담당자 |

---

## Phase 1-A — 최소 MVP (56개 + 6개 보강 = 62개)

### 인증 (7)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 1 | POST | `/auth/login` | Public | 로그인 → JWT 발급 |
| 2 | POST | `/auth/refresh` | Public | 토큰 갱신 |
| 3 | POST | `/auth/logout` | All | 로그아웃 (블랙리스트) |
| 4 | POST | `/auth/password/reset-request` | Public | 비밀번호 재설정 이메일 |
| 5 | POST | `/auth/password/reset` | Public | 비밀번호 재설정 |
| 6 | POST | `/auth/invite/accept` | Public | 초대 수락 및 가입 |
| 7 | GET | `/auth/invite/verify` | Public | 초대 토큰 유효성 확인 |

### 워크스페이스 (2)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 8 | GET | `/workspaces` | All | 사용자의 위탁기관 목록 |
| 9 | GET | `/users/me` | All | 로그인 사용자 정보 |

### 대시보드 (7, +1 in 1-B)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 10 | GET | `/dashboard/summary` | All | KPI 요약 카드 |
| 11 | GET | `/dashboard/platform-trends` | All | 플랫폼별 성과 추이 (라인차트) |
| 12 | GET | `/dashboard/approval-status` | All | 승인 대기 현황 |
| 13 | GET | `/dashboard/recent-contents` | All | 최근 콘텐츠 목록 |
| 14 | GET | `/dashboard/today-schedule` | All | 오늘 예약 게시 |
| 15 | GET | `/dashboard/all-organizations` | AM | 전체 기관 현황 (기관별 channelCount, contentCount, pendingApprovals, lastPublishedAt) |
| 16 | GET | `/dashboard/badge-counts` | All | 사이드바 뱃지 카운트 |

### 콘텐츠 (17, v2.0: +6 variants)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 17 | POST | `/contents` | AM,AO | 새 콘텐츠 작성 |
| 18 | GET | `/contents` | All | 콘텐츠 목록 (필터/페이지네이션) |
| 19 | GET | `/contents/:id` | All | 콘텐츠 상세 |
| 20 | PUT | `/contents/:id` | AM,AO | 콘텐츠 수정 |
| 21 | DELETE | `/contents/:id` | AM,AO | 콘텐츠 삭제 |
| 22 | POST | `/contents/:id/save-draft` | AM,AO | 임시 저장 |
| 23 | POST | `/contents/:id/request-review` | AO | 검토 요청 |
| 24 | GET | `/contents/:id/publish-history` | All | 게시 이력 조회 |
| 25 | POST | `/contents/:id/retry-publish` | AM,AO | 게시 재시도 |
| 26 | POST | `/contents/bulk-action` | AM | 일괄 작업 (삭제/상태변경) |
| 27 | POST | `/contents/:id/cancel-publish` | AM,AO | 예약 게시 취소 |
| 27a | GET | `/contents/:id/versions` | All | 콘텐츠 버전 목록 |
| 27b | GET | `/contents/:id/versions/:version` | All | 특정 버전 상세 |
| 27c | POST | `/contents/:id/versions/:version/restore` | AM,AO | 이전 버전 복원 |
| 27d | POST | `/contents/:id/variants` | AM,AO | 파생본 생성 (v2.0) |
| 27e | GET | `/contents/:id/variants` | All | 파생본 목록 (v2.0) |
| 27f | PUT | `/contents/:id/variants/:vid` | AM,AO | 파생본 수정 (v2.0) |
| 27g | DELETE | `/contents/:id/variants/:vid` | AM,AO | 파생본 삭제 (v2.0) |
| 27h | POST | `/contents/:id/variants/:vid/media` | AM,AO | 파생본 미디어 연결 (v2.0) |
| 27i | DELETE | `/contents/:id/variants/:vid/media/:mid` | AM,AO | 파생본 미디어 해제 (v2.0) |

### 승인 (4)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 28 | GET | `/approvals` | AM,CD | 승인 대기 목록 |
| 29 | GET | `/approvals/:id` | AM,CD | 승인 상세 (currentApprovers 포함) |
| 30 | POST | `/approvals/:id/approve` | CD | 승인 |
| 31 | POST | `/approvals/:id/reject` | CD | 반려 (사유 포함) |

### 채널 (7)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 32 | GET | `/channels` | All | 연동 채널 목록 |
| 33 | POST | `/channels/connect/initiate` | AM | OAuth 연동 시작 |
| 34 | POST | `/channels/connect/callback` | System | OAuth 콜백 |
| 35 | DELETE | `/channels/:id` | AM | 채널 연동 해제 |
| 36 | POST | `/channels/:id/refresh-token` | AM | 토큰 수동 갱신 |
| 37 | GET | `/channels/:id/history` | AM | 연동 이력 |
| 38 | GET | `/channels/api-status` | AM | API Rate Limit 현황 |

### 사용자·권한 (6)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 39 | GET | `/users` | AM | 사용자 목록 |
| 40 | POST | `/users/invite` | AM | 사용자 초대 (이메일) |
| 41 | GET | `/users/:id` | AM | 사용자 상세 |
| 42 | PUT | `/users/:id` | AM | 사용자 정보 수정 |
| 43 | DELETE | `/users/:id` | AM | 사용자 삭제 |
| 44 | GET | `/roles` | AM | 역할 목록 |
| 44a | GET | `/users/invitations` | AM | 발송 초대 목록 |
| 44b | DELETE | `/users/invitations/:id` | AM | 초대 취소 |
| 44c | POST | `/users/invitations/:id/resend` | AM | 초대 재발송 |

### 설정 (6)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 45 | GET | `/organizations` | SA,AM | 기관 목록 |
| 46 | POST | `/organizations` | SA,AM | 기관 등록 |
| 47 | PUT | `/organizations/:id` | SA,AM | 기관 수정 |
| 48 | DELETE | `/organizations/:id` | SA | 기관 삭제 |
| 49 | GET | `/workflows` | AM,CD | 승인 워크플로우 조회 |
| 50 | PUT | `/workflows` | AM | 승인 워크플로우 설정 |

### 검색 (1)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 51 | GET | `/search` | All | 통합 검색 (PG tsvector → Phase 2: Meilisearch) |

### 시스템 관리 (5)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 52 | GET | `/admin/agencies` | SA | 수탁업체 목록 |
| 53 | POST | `/admin/agencies` | SA | 수탁업체 등록 |
| 54 | GET | `/admin/health` | SA | 시스템 상태 확인 |
| 55 | GET | `/admin/announcements` | SA | 시스템 공지 목록 |
| 56 | POST | `/admin/announcements` | SA | 시스템 공지 등록 |

---

## Phase 1-B — MVP 확장 (추가 33개, 누적 89개)

### 대시보드 추가 (1)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 57 | GET | `/dashboard/sentiment-summary` | All | 감성 분석 현황 (도넛차트) |

### 댓글 (8)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 58 | GET | `/comments` | All | 통합 댓글 목록 |
| 59 | GET | `/comments/:id` | All | 댓글 상세 |
| 60 | GET | `/comments/dangerous` | All | 위험 댓글 목록 |
| 61 | POST | `/comments/:id/reply` | AM,AO | 댓글 답글 |
| 62 | POST | `/comments/:id/hide` | AM,AO | 댓글 숨김 |
| 63 | POST | `/comments/:id/delete-request` | AO | 댓글 삭제 요청 |
| 64 | POST | `/comments/:id/ignore` | AM,CD | 위험 댓글 무시 |
| 65 | POST | `/comments/:id/delete-approve` | AM,CD | 댓글 삭제 승인 |

### 답글 템플릿 (4)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 66 | GET | `/reply-templates` | All | 템플릿 목록 |
| 67 | POST | `/reply-templates` | AM,AO | 템플릿 생성 |
| 68 | PUT | `/reply-templates/:id` | AM,AO | 템플릿 수정 |
| 69 | DELETE | `/reply-templates/:id` | AM | 템플릿 삭제 |

### 분석 (3)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 70 | GET | `/analytics/performance` | All | 성과 분석 데이터 |
| 71 | GET | `/analytics/engagement-heatmap` | All | 시간대별 참여율 히트맵 |
| 72 | GET | `/analytics/performance/export` | AM | 성과 데이터 내보내기 (CSV) |

### 알림 (5)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 73 | GET | `/notifications` | All | 알림 목록 (필터/페이지네이션) |
| 74 | PATCH | `/notifications/:id/read` | All | 알림 읽음 처리 |
| 75 | POST | `/notifications/mark-all-read` | All | 전체 읽음 처리 |
| 76 | GET | `/notifications/unread-count` | All | 미읽음 건수 |
| 77 | GET | `/sse/events` | All | SSE 실시간 스트림 |

### 알림 설정 (4)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 78 | GET | `/notification-settings` | All | 알림 설정 조회 |
| 79 | PUT | `/notification-settings` | All | 알림 설정 변경 |
| 80 | POST | `/notification-settings/telegram/test` | All | 텔레그램 테스트 발송 |
| 81 | POST | `/notification-settings/telegram/channels` | AM | 텔레그램 채널 설정 |

### 감사 로그 (3)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 82 | GET | `/audit-logs` | AM,CD | 감사 로그 목록 |
| 83 | GET | `/audit-logs/:id` | AM,CD | 감사 로그 상세 |
| 84 | GET | `/audit-logs/export` | AM | 감사 로그 내보내기 (CSV/PDF) |

### AI (4)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 85 | POST | `/ai/generate-title` | AM,AO | AI 제목 생성 (F02) |
| 86 | POST | `/ai/generate-description` | AM,AO | AI 설명문 생성 (F02) |
| 87 | POST | `/ai/generate-hashtags` | AM,AO | AI 해시태그 생성 (F02) |
| 88 | GET | `/admin/ai-usage` | SA | AI 사용량 모니터링 |

### 시스템 관리 추가 (1)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 89 | GET | `/admin/rate-limits` | SA | Rate Limit 현황 |

---

## Phase 2 — AI 콘텐츠 고도화 (추가 20개, 누적 109개)

### 캘린더 (4)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 90 | GET | `/calendar/events` | All | 캘린더 이벤트 목록 |
| 91 | PATCH | `/calendar/events/:id/reschedule` | AM,AO | 일정 변경 |
| 92 | GET | `/calendar/holidays` | All | 공휴일/기념일 목록 |
| 93 | PUT | `/calendar/holidays` | AM | 공휴일 설정 |

### 미디어 (8)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 94 | GET | `/media` | All | 미디어 라이브러리 목록 |
| 95 | POST | `/media/upload` | AM,AO | ~~미디어 업로드~~ (DEPRECATED: 콘텐츠 작성에서 처리) |
| 96 | GET | `/media/:id` | All | 미디어 상세 |
| 97 | PUT | `/media/:id` | AM,AO | 미디어 메타 수정 |
| 98 | DELETE | `/media/:id` | AM | 미디어 삭제 |
| 99 | GET | `/media/folders` | All | 폴더 목록 |
| 100 | POST | `/media/folders` | AM,AO | 폴더 생성 |
| 101 | POST | `/media/shortform` | AM,AO | 숏폼 생성 (F15) |
| — | POST | `/media/presigned-upload` | AM,AO | ~~Presigned URL 발급~~ (DEPRECATED: 콘텐츠 작성에서 처리) |

### AI (8)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 102 | POST | `/ai/tone-transform` | AM,AO | 톤앤매너 변환 (F17) |
| 103 | POST | `/ai/content-review` | AM,AO | 표현 가이드 검수 (F21) |
| 104 | POST | `/ai/generate-reply` | AM,AO | AI 답글 초안 (F05) |
| 105 | POST | `/ai/generate-subtitles` | AM,AO | AI 자막 생성 (F03, 비동기) |
| 106 | POST | `/ai/suggest-effects` | AM,AO | AI 효과음 제안 (F03) |
| 107 | POST | `/ai/extract-shortform` | AM,AO | AI 숏폼 구간 추출 (F15, 비동기) |
| 108 | POST | `/ai/improve-template` | AM,AO | AI 템플릿 개선 (F05) |
| 109 | GET | `/ai/jobs/:jobId` | All | 비동기 AI 작업 상태 조회 |

---

## Phase 3 — 분석·보고 고도화 (추가 9개, 누적 118개)

### 분석 (2)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 110 | GET | `/analytics/sentiment-trend` | All | 여론 동향 시계열 (F18) |
| 117 | GET | `/analytics/prediction` | All | 성과 예측 데이터 (F20) |

### 리포트 (6)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 111 | GET | `/reports` | AM,CD | 리포트 목록 |
| 112 | POST | `/reports/generate` | AM,AO | 리포트 AI 생성 (F19, 비동기) |
| 113 | GET | `/reports/:id` | AM,CD | 리포트 상세 |
| 114 | PUT | `/reports/:id` | AM,AO | 리포트 편집 |
| 115 | POST | `/reports/:id/finalize` | AM | 리포트 확정 |
| 116 | GET | `/reports/:id/download` | AM,CD | 리포트 PDF 다운로드 |

### AI (1)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 118 | POST | `/ai/optimal-time` | AM,AO | 최적 게시 시간 추천 (F20) |

---

## Phase 4 — 확장 기능 (추가 4개, 총 122개)

### 벤치마크 (2)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 119 | GET | `/analytics/benchmark` | AM,CD | 벤치마크 분석 (F23) |
| 120 | GET | `/analytics/benchmark/organizations` | AM | 기관 비교 (F23) |

### AI (2)

| # | Method | Endpoint | 역할 | 설명 |
|---|---|---|---|---|
| 121 | POST | `/ai/generate-thumbnail` | AM,AO | AI 썸네일 생성 (F16) |
| 122 | POST | `/ai/translate` | AM,AO | AI 다국어 번역 (F22) |

---

## 도메인별 엔드포인트 수 요약

| 도메인 | 수 | Phase | 도메인 | 수 | Phase |
|---|:---:|---|---|:---:|---|
| 인증 | 7 | 1-A | 알림 | 5 | 1-B |
| 워크스페이스 | 2 | 1-A | 감사 로그 | 3 | 1-B |
| 대시보드 | 8 | 1-A/1-B | AI | 14 | 1-B~4 |
| 콘텐츠 | 14 | 1-A | 검색 | 1 | 1-A |
| 승인 | 4 | 1-A | 시스템 관리 | 7 | 1-A/1-B |
| 캘린더 | 4 | 2 | 채널 | 7 | 1-A |
| 댓글 | 8 | 1-B | 사용자·권한 | 9 | 1-A |
| 답글 템플릿 | 4 | 1-B | 설정 | 10 | 1-A/1-B |
| 미디어 | 8 | 2 | 분석·리포트 | 13 | 1-B~4 |
| | | | **합계** | **128** | |
