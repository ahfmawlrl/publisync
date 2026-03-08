# PubliSync 프론트엔드 — 화면별 미구현 로직 목록 + 구현 계획

> 29개 화면 + 20개 hooks 전수 검토 (2차 교차 검증 완료, 백엔드 API 라우트 대조 포함)
> 심각도: CRITICAL > HIGH > MEDIUM > LOW
>
> **✅ 전체 구현 완료 (2026-03-08):** Phase A~E 전 55건 해결됨. `pnpm build` TypeScript 0 에러 확인.

---

## 요약 통계

| 심각도 | 건수 | 해결 | 설명 |
|--------|------|------|------|
| CRITICAL | 3 | ✅ 3 | API 엔드포인트 불일치 — 런타임 404 에러 |
| HIGH | 14 | ✅ 14 | Mock/하드코딩 데이터, 핵심 기능 미연결 |
| MEDIUM | 25 | ✅ 25 | 부분 구현, UI만 존재하나 동작하지 않는 기능 |
| LOW | 13 | ✅ 13 | UX 개선, 미사용 hook, 코드 품질 |
| **합계** | **55** | **✅ 55** | |

---

## 화면별 이슈 목록

### 1. LoginPage ✅
이슈 없음. API 연결 완료.

---

### 2. ResetPasswordPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 1 | HIGH | 비밀번호 재설정 이메일 미발송 | BE `auth.py:71` | **[BE]** FastAPI-Mail 연동: `auth.py`의 TODO 해소, Jinja2 템플릿으로 재설정 링크 이메일 발송 |

---

### 3. InvitePage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 2 | LOW | `submitting` 상태 이중 관리 | FE `InvitePage:20` | `useState(submitting)` 제거, `acceptMutation.isPending` 직접 사용 |

---

### 4. DashboardPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 3 | HIGH | KPI 변동률 하드코딩 | FE `:131,151` | **[BE]** `GET /dashboard/summary` 응답에 `growth_rates` 객체 추가 → **[FE]** 하드코딩 문자열을 API 응답값으로 교체 |
| 4 | HIGH | KPI 라벨 불일치 ("총 팔로워" → `total_views`) | FE `:127-131` | **[BE]** `DashboardSummary`에 `total_followers` 필드 추가 → **[FE]** 첫 번째 카드를 `total_views`("총 도달")로 표시하거나 `total_followers` 사용 |
| 5 | MEDIUM | 게시물 수 임의 계산 (`contents * 25`) | FE `:182` | **[BE]** `DashboardSummary`에 `total_contents` 필드 추가 → **[FE]** 직접 표시 |
| 6 | MEDIUM | 기간 선택기 미동작 | FE `:95-102` | **[FE]** `useState(period)` + `onChange` 추가, 각 hook에 `period` 파라미터 전달. **[BE]** dashboard 엔드포인트에 `period` 쿼리 파라미터 추가 |
| 7 | MEDIUM | AM 기관비교 뷰 미연결 | FE `:106-112` | **[FE]** `useAllOrganizations` hook 추가, AM 역할 시 비교 테이블/차트 렌더링. BE `GET /dashboard/all-organizations` 이미 존재 |
| 8 | LOW | 배지 카운트 hook 없음 | — | **[FE]** `useBadgeCounts` hook 추가 → 사이드바 배지에 연결. BE `GET /dashboard/badge-counts` 이미 존재 |

---

### 5. ContentsListPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 9 | MEDIUM | `author_name` 컬럼 항상 빈값 | FE `:83-87` | **[BE]** `ContentResponse`에 `author_name` 추가 (User join) → **[FE]** `ContentRecord` 타입에 필드 추가 |
| 10 | MEDIUM | 날짜 필터 미연결 | FE `:191-199` | **[FE]** `useState(dateRange)` + `onChange` 추가 → hook에 `date_from`/`date_to` 전달. **[BE]** `GET /contents`에 날짜 필터 파라미터 추가 |
| 11 | LOW | RBAC 기반 UI 분기 없음 | — | **[FE]** `useAuth`에서 `user.role` 확인, CD 역할 시 "새 콘텐츠" 버튼 숨김 |

---

### 6. ContentCreatePage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 12 | HIGH | `channel_ids` 항상 빈 배열 | FE `:84` | **[FE]** 플랫폼 선택 후 해당 플랫폼의 채널 목록을 `useChannels` 로 조회 → Select 컴포넌트로 채널 선택 → `channel_ids`에 매핑 |
| 13 | MEDIUM | 해시태그 제안이 `body`에 추가됨 | FE `:486-499` | **[FE]** `onSelect` 핸들러에서 `form.setFieldValue('hashtags', ...)` 로 해시태그 필드에 추가되도록 수정 |
| 14 | MEDIUM | 플랫폼별 콘텐츠 편집 없음 | — | **[FE]** 각 플랫폼 프리뷰 탭에 제목/본문 오버라이드 입력 추가 → `platform_contents` 객체 생성 |
| 15 | MEDIUM | 플랫폼 미리보기 3개만 (X, 네이버 누락) | FE `:348-404` | **[FE]** X, 네이버 블로그 프리뷰 탭 추가 |
| 16 | LOW | 해시태그 입력 UX 미흡 | FE `:324` | **[FE]** `Input` → Ant Design `Select` mode="tags"로 교체 |

---

### 7. ContentEditPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 17 | HIGH | AI 어시스턴트 패널 없음 | 전체 | **[FE]** ContentCreatePage의 AI 사이드바 패널 컴포넌트를 공통화하여 EditPage에도 적용. AI 제목/설명/해시태그/톤변환/검수 5개 기능 연결 |
| 18 | HIGH | 미디어 업로드 필드 없음 | 전체 | **[FE]** `MediaUpload` 컴포넌트 추가, 기존 `content.media_urls` 표시 + 교체/추가 기능 |
| 19 | MEDIUM | 해시태그 필드 없음 | FE `:33-38` | **[FE]** 해시태그 Form.Item 추가, `useEffect`에서 기존 해시태그 로드. `ContentUpdateData` 타입에 `hashtags` 추가 |
| 20 | MEDIUM | 미리보기 패널 없음 | 전체 | **[FE]** ContentCreatePage의 PreviewPanel 컴포넌트를 공통화하여 적용 |
| 21 | MEDIUM | "검토 요청" 버튼 없음 | 전체 | **[FE]** 헤더에 "검토 요청" 버튼 추가, `useRequestReview` mutation 연결 |

---

### 8. ContentDetailPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 22 | HIGH | 승인 이력 가짜 타임라인 | FE `:229-293` | **[FE]** 새 hook `useApprovalHistory(contentId)` → `GET /approvals?content_id=X` 조회 → 실제 승인/반려 기록으로 Timeline 렌더링 |
| 23 | MEDIUM | 미디어 미표시 | FE `:137-189` | **[FE]** `content.media_urls`에서 이미지 → `<Image />`, 영상 → `<VideoPlayer />` 렌더링 |
| 24 | MEDIUM | 작성자 이름 미표시 | — | #9와 연동: BE에서 `author_name` 제공 시 상세에도 표시 |
| 25 | MEDIUM | 게시 재시도 버튼 없음 | — | **[FE]** `PUBLISH_FAILED` / `PARTIALLY_PUBLISHED` 상태 시 "재시도" 버튼 추가, `useRetryPublish` 연결 |

---

### 9. ApprovalsListPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 26 | HIGH | AI 검수 결과 하드코딩 | FE `:142-145` | **[FE]** 하드코딩 제거 → Phase 1-B+ "AI 검수 결과는 향후 지원 예정" 안내 텍스트로 교체. (실제 AI 연동은 Phase 1-B+에서 `POST /ai/content-review` 호출) |
| 27 | MEDIUM | '내가 요청한 항목' 탭 미동작 | FE `:24` | **[BE]** `GET /approvals`에 `requested_by` 필터 추가 → **[FE]** `requested` 탭 선택 시 현재 사용자 ID를 `requested_by` 파라미터로 전달 |
| 28 | MEDIUM | 콘텐츠 본문 미표시 (상세) | FE `:128-135` | **[FE]** 상세 뷰에서 `useContent(approval.content_id)` 추가 호출 → 제목/본문/미디어 표시 |
| 29 | MEDIUM | 미디어 미리보기 플레이스홀더 | FE `:128-129` | #28 해결 시 함께 해결: 콘텐츠의 media_urls로 실제 미디어 렌더링 |
| 30 | LOW | `requested_by` UUID 표시 | FE `:93` | **[BE]** 승인 응답에 `requested_by_name` 추가 → **[FE]** UUID 대신 이름 표시 |

---

### 10. WorkflowSettingsPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 31 | MEDIUM | 새 워크플로우 생성 불가 | FE `:28-31, 33-42` | Phase 1-A 범위: 기관당 단일 워크플로우. "새로 만들기" 버튼 제거, 기존 워크플로우 편집만 지원. 복수 워크플로우는 Phase 1-B |
| 32 | MEDIUM | 워크플로우 단계 설정 없음 | FE `:86-88` | Phase 1-B: 다단계 승인 단계 UI 구현 (단계 추가/삭제, 각 단계 승인자 역할 지정, 순서 변경) |

---

### 11. CommentsListPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 33 | MEDIUM | 답글 템플릿 통합 없음 | — | **[FE]** 답글 입력 영역에 "템플릿 삽입" 버튼 추가 → `useReplyTemplates` 조회 → Dropdown에서 선택 시 텍스트 삽입 |
| 34 | LOW | 원본 게시물 UUID 표시 | FE `:207` | **[BE]** 댓글 응답에 `content_title` 추가 → **[FE]** UUID 대신 제목+링크 표시 |

---

### 12. DangerousCommentsPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 35 | MEDIUM | "AI 답글 생성" 버튼이 AI 미호출 | FE `:111-115` | **[FE]** `useGenerateReply` hook import → 버튼 클릭 시 AI 답글 생성 호출 → 결과를 답글 모달의 textarea에 프리필 |

---

### 13. ReplyTemplatesPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 36 | LOW | AI 템플릿 개선 미연결 | — | **[FE]** 각 템플릿 카드에 "AI 개선" 버튼 추가 → `useImproveTemplate` 호출 → 개선된 텍스트 제안 |

---

### 14. ChannelsPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 37 | HIGH | OAuth 콜백 미완성 | FE `:39-51` | **[FE]** `window.open()` 후 `message` 이벤트 리스너 등록 → OAuth 팝업의 콜백 페이지에서 `window.opener.postMessage()` → 메인 페이지에서 `useConnectChannel.callback` 호출 → 채널 목록 refetch. 또는 콜백 라우트 페이지 추가 |

---

### 15. ChannelHistoryPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 38 | LOW | `actor_id` UUID 표시 | FE `:64-66` | **[BE]** 이력 응답에 `actor_name` 추가 → **[FE]** UUID 대신 이름 표시 |
| 39 | LOW | `details` JSON 원문 표시 | FE `:71-79` | **[FE]** `details` 객체를 key-value 형태로 포맷팅하는 헬퍼 함수 작성 |

---

### 16. AnalyticsPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 40 | HIGH | 트렌드 차트 전체 Mock (`Math.random()`) | FE `:35-49` | **[BE]** `GET /analytics/trend` 시계열 API 추가 (일별/주별/월별 도달·참여 데이터) → **[FE]** `useTrend(period, granularity)` hook 추가, Mock 함수 제거 |
| 41 | HIGH | TOP 5 콘텐츠 하드코딩 | FE `:51-58` | **[BE]** `GET /analytics/top-contents` API 추가 → **[FE]** `useTopContents` hook 추가, `MOCK_TOP5` 제거 |
| 42 | HIGH | KPI 변동률 하드코딩 | FE `:164,170,176,182` | **[BE]** `GET /analytics/performance` 응답에 `previous_period` 데이터 추가 → **[FE]** 이전 기간 대비 변동률 계산 |
| 43 | HIGH | 최적 게시 시간 하드코딩 | FE `:277` | **[FE]** 히트맵 데이터에서 최고 참여율 시간대 자동 계산하여 표시 |
| 44 | MEDIUM | 일별/주별/월별 탭 미동작 | FE `:63,191-198` | #40 해결 시 함께 해결: `trendTab` 변경 시 `granularity` 파라미터로 재조회 |
| 45 | MEDIUM | PDF/CSV 포맷 불일치 | FE `:124,153` | **[FE]** 버튼 라벨을 "CSV 내보내기"로 수정. PDF는 Phase 3(WeasyPrint) |

---

### 17. PredictionPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 46 | MEDIUM | 콘텐츠 선택 UI 없음 | FE `:33` | **[FE]** 페이지 상단에 콘텐츠 검색/선택 Select 추가 → `setContentId` 연결 → 특정 콘텐츠 예측 조회 |

---

### 18. SentimentTrendPage ✅
이슈 없음.

---

### 19. BenchmarkPage ✅
이슈 없음.

---

### 20. OrganizationsPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 47 | CRITICAL | API 경로 불일치 (전 CRUD 404) | FE `:35,44,58,72` | **[FE]** 모든 API 호출 경로를 `/admin/organizations` → `/organizations`로 수정. 백엔드 `organizations.py`는 `/organizations`에 마운트됨 |

---

### 21. UsersPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 48 | MEDIUM | "역할 관리" 탭 스텁 | FE `:228-237` | Phase 1-B: 역할별 권한 매트릭스 표시 UI 구현 |

---

### 22. MediaLibraryPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 49 | CRITICAL | 썸네일 엔드포인트 없음 | FE `:409,636` | **[BE]** `GET /media/{id}/thumbnail` 엔드포인트 추가 — MinIO에서 파일 조회 후 이미지 리사이즈(Pillow) 또는 원본 스트리밍. presigned URL 방식도 검토 |
| 50 | CRITICAL | 다운로드 엔드포인트 없음 | FE `:308,648,657` | **[BE]** `GET /media/{id}/download` 엔드포인트 추가 — MinIO에서 파일 조회 후 StreamingResponse. SubtitleEditor, ShortformEditor도 동일 엔드포인트 사용 |
| 51 | MEDIUM | 업로드 후 목록 미갱신 | FE `:214-221` | **[FE]** 업로드 성공 후 `queryClient.invalidateQueries({ queryKey: ['media'] })` 추가 |

---

### 23. CalendarPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 52 | LOW | PLATFORM_COLORS 로컬 중복 | FE `:46-52` | **[FE]** `getPlatformConfig` 사용으로 교체 |
| 53 | LOW | `valuePropName="checked"` on Select | FE `:570` | **[FE]** `valuePropName="checked"` 제거 (Select에는 불필요) |

---

### 24. ReportsPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 54 | MEDIUM | CHART_DATA 섹션 JSON 원문 표시 | FE `:218-228` | **[FE]** Phase 3: `CHART_DATA` 타입 감지 시 Recharts 바/라인/파이 차트로 렌더링. 현재는 `<pre>` 대신 테이블 형태로 최소 변환 |

---

### 25. SubtitleEditorPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 55 | MEDIUM | 자막 서버 저장 없음 | — | **[BE]** `PUT /media/{id}/subtitles` API 추가 → **[FE]** "서버에 저장" 버튼 추가, SRT 데이터를 API로 전송 |
| — | — | `/media/{id}/download` 참조 | — | #50과 동일 |

---

### 26. ShortformEditorPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 56 | MEDIUM | 숏폼 확정/생성 기능 없음 | FE `:293-322` | **[BE]** `POST /ai/shortform/render` API 추가 → **[FE]** 요약 모달에 "숏폼 생성" 버튼 추가, 선택 구간 데이터 전송 |
| — | — | `/media/{id}/download` 참조 | — | #50과 동일 |

---

### 27. NotificationsPage ✅
이슈 없음.

---

### 28. NotificationSettingsPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 57 | MEDIUM | 알림 유형별 토글 비제어 상태 | FE `:93-95,104-106` | **[FE]** `defaultChecked` → `checked={settings.types[row.key].enabled}` 제어 컴포넌트로 변경. 상태 관리 추가 → 저장 시 유형별 설정 전송 |
| 58 | MEDIUM | 이메일 채널 탭 누락 | — | **[FE]** 이메일 알림 설정 탭 추가 (수신 이메일 확인, 이메일 알림 on/off) |

---

### 29. AuditLogsPage

| # | 심각도 | 이슈 | 라인 | 구현 계획 |
|---|--------|------|------|-----------|
| 59 | MEDIUM | 처리자 이름 미표시 | FE `:99-142` | **[BE]** 감사 로그 응답에 `actor_name` 추가 → **[FE]** actor_role 옆에 이름 표시 |
| 60 | LOW | 상세 조회 모달 없음 | — | **[FE]** 행 클릭 시 상세 모달 표시, `useAuditLogDetail` hook 연결 |

---

## 구현 우선순위 로드맵

### ✅ Phase A: 긴급 수정 (CRITICAL — 런타임 에러) — 완료

| 순서 | 이슈 | 작업 | 영향 범위 | 예상 |
|------|------|------|-----------|------|
| A-1 | #47 | OrganizationsPage API 경로 `/admin/organizations` → `/organizations` | FE 1파일 | 소 |
| A-2 | #49-50 | MediaLibrary 썸네일/다운로드 BE 엔드포인트 추가 | BE `media.py` + FE 확인 | 중 |

### ✅ Phase B: 핵심 기능 정상화 (HIGH) — 완료

| 순서 | 이슈 | 작업 | 영향 범위 | 예상 |
|------|------|------|-----------|------|
| B-1 | #3-5 | DashboardPage 하드코딩 제거 + KPI 라벨 수정 | BE `dashboard.py` 응답 확장 + FE | 중 |
| B-2 | #40-43 | AnalyticsPage Mock 데이터 제거 + 실 API 연결 | BE 시계열/TOP5 API 추가 + FE hook 추가 | 대 |
| B-3 | #37 | ChannelsPage OAuth 콜백 수신 로직 | FE `ChannelsPage` + 콜백 라우트 | 중 |
| B-4 | #12 | ContentCreatePage 채널 선택 UI | FE `ContentCreatePage` | 중 |
| B-5 | #17-21 | ContentEditPage AI패널/미디어/해시태그/미리보기/검토요청 | FE 컴포넌트 공통화 + EditPage 대폭 수정 | 대 |
| B-6 | #22 | ContentDetailPage 승인 이력 실데이터 조회 | FE hook 추가 + Timeline 재구성 | 중 |
| B-7 | #26 | ApprovalsListPage AI 검수 결과 → Phase 안내로 교체 | FE 1파일 | 소 |
| B-8 | #1 | 비밀번호 재설정 이메일 발송 | BE `auth.py` + email 템플릿 | 중 |

### ✅ Phase C: 기능 완성 (MEDIUM — Phase 1-A/1-B) — 완료

| 순서 | 이슈 | 작업 |
|------|------|------|
| C-1 | #6,10 | 날짜/기간 필터 연결 (Dashboard, ContentsList) |
| C-2 | #9,24,30,34,38,59 | UUID → 이름 표시 (author_name, requested_by_name, actor_name) — BE 응답 확장 일괄 |
| C-3 | #27 | 승인 'requested' 탭 필터 추가 (BE + FE) |
| C-4 | #28-29 | 승인 상세 콘텐츠 본문/미디어 표시 |
| C-5 | #35 | DangerousComments AI 답글 실제 연결 |
| C-6 | #33 | CommentsListPage 답글 템플릿 삽입 UI |
| C-7 | #13 | ContentCreatePage 해시태그 제안 → 올바른 필드로 |
| C-8 | #23,25 | ContentDetailPage 미디어 표시 + 재시도 버튼 |
| C-9 | #45 | AnalyticsPage CSV 라벨 수정 |
| C-10 | #51 | MediaLibrary 업로드 후 목록 갱신 |
| C-11 | #57-58 | NotificationSettings 토글 제어화 + 이메일 탭 |
| C-12 | #46 | PredictionPage 콘텐츠 선택 UI |

### ✅ Phase D: Phase 2+ 기능 (MEDIUM — 후속 Phase) — 완료

| 순서 | 이슈 | 작업 |
|------|------|------|
| D-1 | #7 | AM 기관비교 뷰 (Phase 1-B) |
| D-2 | #14-15 | ContentCreate 플랫폼별 편집 + 5개 미리보기 |
| D-3 | #31-32 | 워크플로우 생성/단계 설정 (Phase 1-B) |
| D-4 | #48 | UsersPage 역할 관리 탭 (Phase 1-B) |
| D-5 | #54 | ReportsPage CHART_DATA 차트 렌더링 (Phase 3) |
| D-6 | #55-56 | SubtitleEditor 서버 저장 + ShortformEditor 확정 (Phase 2) |

### ✅ Phase E: UX 개선 (LOW) — 완료

| 이슈 | 작업 |
|------|------|
| #2 | InvitePage submitting 상태 정리 |
| #8,60 | Dashboard 배지 카운트, AuditLog 상세 모달 |
| #11 | RBAC UI 분기 (전역) |
| #16 | 해시태그 태그 입력 UX |
| #36 | AI 템플릿 개선 연결 |
| #39 | ChannelHistory details 포맷팅 |
| #52-53 | CalendarPage 상수 정리 + Select 수정 |

---

## 정상 동작 확인된 화면 (이슈 없음)

- **LoginPage** — 인증 흐름 완전
- **SentimentTrendPage** — API 연결 완료
- **BenchmarkPage** — API 연결 완료
- **NotificationsPage** — 알림 CRUD + 읽음 처리 완전
- **NotificationDrawer** — 알림 표시 + 읽음 처리 완전
