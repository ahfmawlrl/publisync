# ContentEditorPage 영상 중심 재설계 계획

## 1. 현재 문제점 분석

### 1-1. 구조적 문제
- **텍스트 중심 레이아웃**: 영상은 "미디어 소재" 폼 필드에 부수적으로 첨부
- **자막/숏폼 분리**: 별도 페이지(`/ai/subtitle-editor`, `/ai/shortform-editor`)로만 진입 → 콘텐츠 작성 흐름 단절
- **효과음/이모지 누락**: 백엔드 API(`useSuggestEffects`)와 타입(`AiSuggestEffectsRequest`)은 존재하지만 UI 미구현

### 1-2. AI 기능 버그/문제
| 문제 | 위치 | 설명 |
|---|---|---|
| **AI 제목 제안이 본문 의존** | `ContentEditorPage:327-334` | `getContentText()`가 `body` 10자 이상 요구 → 제목 먼저 생성 불가 |
| **AI 해시태그도 본문 의존** | 동일 | 제목만으로도 해시태그 추천 가능해야 함 |
| **AI 버튼 중복** | `ContentEditorPage:434-446` + `509-513` | 제목 필드 아래 + AI 어시스턴트 패널에 동일 기능 2번 반복 |
| **AI 제안 결과 미적용 (해시태그)** | `ContentEditorPage:463-476` | 해시태그 mutation은 `data.hashtags`를 반환하는데 AiSuggestionPanel이 없어 결과 표시 안 됨 |
| **효과음/이모지 UI 없음** | 전체 | `useSuggestEffects` 훅 존재하지만 ContentEditorPage에서 미사용 |

---

## 2. 재설계 방향

### 2-1. 핵심 원칙
1. **영상 플레이어가 메인** — 화면 상단/중심에 VideoPlayer + WaveformViewer
2. **타임라인 기반 도구 바** — 자막/효과음/이모지/숏폼을 인라인 패널로 전환
3. **텍스트 편집은 모달** — 제목/본문/해시태그, 플랫폼별 커스터마이즈는 모달로 이동
4. **미디어 타입 적응** — 영상이면 플레이어, 이미지면 갤러리 뷰, 없으면 업로드 영역

### 2-2. 새로운 레이아웃

```
┌────────────────────────────────────────────────────────────────┐
│ ← 뒤로  새 콘텐츠 작성              [임시 저장] [검수 요청]     │
├────────────────────────────────────────────────────────────────┤
│ ┌─ 미디어 영역 (메인) ──────────────────────────────────────┐  │
│ │  ┌────────────────────────────────────────────┐           │  │
│ │  │         VideoPlayer (16:9)                 │           │  │
│ │  │         또는 이미지 갤러리                   │           │  │
│ │  │         또는 업로드 드롭존                   │           │  │
│ │  └────────────────────────────────────────────┘           │  │
│ │  ┌────────────────────────────────────────────┐           │  │
│ │  │  WaveformViewer (영상 있을 때만)            │           │  │
│ │  └────────────────────────────────────────────┘           │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                │
│ ┌─ 도구 바 (Segmented) ─────────────────────────────────────┐  │
│ │ [📝 콘텐츠 정보] [🎬 자막] [🎵 효과음] [😊 이모지]        │  │
│ │ [✂️ 숏폼 추출] [🤖 AI 어시스턴트] [📱 플랫폼 설정]        │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                │
│ ┌─ 활성 패널 (도구 바 선택에 따라 전환) ─────────────────────┐  │
│ │  (아래 섹션 2-3 ~ 2-9 참조)                                │  │
│ └───────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

### 2-3. 패널: 콘텐츠 정보 (기본 활성)

**모달이 아닌 인라인 패널** — 가장 기본적인 정보이므로 기본 표시.

```
┌─ 콘텐츠 정보 ──────────────────────────────────────────┐
│ 제목: [콘텐츠 제목 입력________________] [AI 제안 ▾]   │
│ 본문: [콘텐츠 본문을 작성하세요                    ]   │
│       [                                            ]   │
│ 해시태그: [#서울시] [#정책브리핑] [+]     [AI 추천 ▾]  │
│ 예약 게시: [2026-03-15 09:00 ▾]                        │
└────────────────────────────────────────────────────────┘
```

- AI 제안 버튼을 Dropdown으로 통합 (중복 제거)
- AI 제목 제안: 제목 또는 본문 중 하나만 있어도 동작하도록 수정

### 2-4. 패널: 자막 편집 (SubtitleEditorPage 인라인화)

SubtitleEditorPage를 props 기반 컴포넌트(`SubtitlePanel`)로 리팩터링.

```
┌─ 자막 편집 ─────────────────────────────────────────────┐
│ [AI 자막 생성] [서버에 저장] [SRT 내보내기]    [+ 추가]  │
│ ┌─ 진행 상태 (AI 작업 중일 때) ─────────────────────┐   │
│ │ ■ 처리 중  72%  ████████░░░░                      │   │
│ └───────────────────────────────────────────────────┘   │
│ ┌─ 자막 목록 ───────────────────────────────────────┐   │
│ │ #1  00:00:01,000 ~ 00:00:03,500                   │   │
│ │     [안녕하세요 서울시에서 전합니다___________] [삭제]│   │
│ │ #2  00:00:03,500 ~ 00:00:06,200                   │   │
│ │     [오늘 소개할 정책은___________________] [삭제]  │   │
│ └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

- `assetId`를 props로 전달 (첨부된 영상의 media asset ID)
- VideoPlayer는 상단 메인 영역 공유 (별도 인스턴스 X)
- WaveformViewer도 상단 공유

### 2-5. 패널: 효과음 (신규)

```
┌─ 효과음 ────────────────────────────────────────────────┐
│ [AI 효과음 추천]                                         │
│ ┌─ 타임라인 ────────────────────────────────────────┐   │
│ │ 00:05  🔔 알림음          [미리듣기] [삭제]        │   │
│ │ 00:12  👏 박수 효과음      [미리듣기] [삭제]        │   │
│ │ 00:30  🎵 전환 효과음      [미리듣기] [삭제]        │   │
│ └───────────────────────────────────────────────────┘   │
│ [+ 수동 추가]  시점: [00:00] 종류: [효과음 선택 ▾]      │
└─────────────────────────────────────────────────────────┘
```

- `useSuggestEffects` 훅 활용
- AI가 영상 맥락 분석 후 적절한 시점에 효과음 추천
- 수동 추가도 지원 (Fallback 원칙)

### 2-6. 패널: 이모지/스티커 (신규)

```
┌─ 이모지/스티커 ─────────────────────────────────────────┐
│ [AI 이모지 추천]                                         │
│ ┌─ 타임라인 ────────────────────────────────────────┐   │
│ │ 00:03  😊  (자막 "안녕하세요"에 매칭)  [삭제]      │   │
│ │ 00:15  🎉  (자막 "축하합니다"에 매칭)  [삭제]      │   │
│ └───────────────────────────────────────────────────┘   │
│ [+ 수동 추가]  시점: [00:00] 이모지: [😊 선택]          │
└─────────────────────────────────────────────────────────┘
```

- 자막 텍스트와 연동하여 AI가 적절한 이모지 추천
- 수동 추가 지원

### 2-7. 패널: 숏폼 추출 (ShortformEditorPage 인라인화)

ShortformEditorPage를 props 기반 컴포넌트(`ShortformPanel`)로 리팩터링.

```
┌─ 숏폼 추출 ─────────────────────────────────────────────┐
│ [AI 구간 추출]                       [선택한 구간 확인]   │
│ ┌─ 클립 목록 ───────────────────────────────────────┐   │
│ │ ☑ 구간 1 "하이라이트" 00:15~00:47 [32초] [미리보기]│   │
│ │ ☑ 구간 2 "핵심 정책"  01:02~01:30 [28초] [미리보기]│   │
│ │ ☐ 구간 3 "엔딩"      02:10~02:55 [45초] [미리보기]│   │
│ │                     선택: 2개 / 총 1분 00초         │   │
│ └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 2-8. 패널: AI 어시스턴트

기존 AI 기능 통합 (톤 변환, 콘텐츠 검수, 번역, 썸네일).

```
┌─ AI 어시스턴트 ─────────────────────────────────────────┐
│ [톤 변환]  [콘텐츠 검수]  [번역]  [썸네일 생성]          │
│                                                          │
│ (선택한 기능의 UI가 여기에 인라인 표시)                    │
│ ┌─ 톤 변환 ─────────────────────────────────────────┐   │
│ │ 플랫폼: [Instagram ▾]  톤: [캐주얼 ▾]  [변환]     │   │
│ │ 결과 1: "여러분~ 봄맞이..."  95%  [사용하기]       │   │
│ │ 결과 2: "안녕! 이번 축제..."  87%  [사용하기]      │   │
│ └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 2-9. 패널: 플랫폼 설정

플랫폼 선택, 채널 배정, 게시 모드, 미리보기 통합.

```
┌─ 플랫폼 설정 ───────────────────────────────────────────┐
│ ☑ YouTube  ☑ Instagram  ☐ Facebook  ☐ X  ☐ 블로그     │
│ 게시 모드: [전체 동일 ○ / 플랫폼별 맞춤 ●]              │
│                                                          │
│ [YouTube] [Instagram]                          ← 탭     │
│ ┌─ YouTube 변형본 ──────────────────────────────────┐   │
│ │ 채널: [모름지기 ▾]                                │   │
│ │ 제목: [________________] (비우면 공통 사용)        │   │
│ │ 본문: [________________] (비우면 공통 사용)        │   │
│ │ 해시태그: [___________] (비우면 공통 사용)          │   │
│ │ [AI 제목] [AI 본문] [AI 해시태그]                  │   │
│ │ ┌─ 미리보기 ─────────────────────────────────┐    │   │
│ │ │ YouTube 16:9 | 제목 | 본문 | #태그         │    │   │
│ │ └───────────────────────────────────────────-┘    │   │
│ └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 3. AI 기능 버그 수정

### 3-1. `getContentText` 개선
```typescript
// Before: body만 확인 → 제목만 있을 때 AI 불가
const getContentText = (): string | null => {
  const body = form.getFieldValue('body') as string | undefined;
  if (!body || body.trim().length < 10) {
    message.warning('AI 제안을 받으려면 본문을 10자 이상 입력하세요.');
    return null;
  }
  return body.trim();
};

// After: 제목 + 본문 합산, 어느 하나만 있어도 동작
const getContentText = (): string | null => {
  const title = form.getFieldValue('title') as string | undefined;
  const body = form.getFieldValue('body') as string | undefined;
  const combined = [title, body].filter(Boolean).join('\n').trim();
  if (combined.length < 5) {
    message.warning('AI 제안을 받으려면 제목 또는 본문을 5자 이상 입력하세요.');
    return null;
  }
  return combined;
};
```

### 3-2. AI 버튼 중복 제거
- 제목 필드 아래의 인라인 AI 버튼 제거
- 해시태그 필드 아래의 인라인 AI 버튼 제거
- 콘텐츠 정보 패널에서 Dropdown 버튼으로 통합

### 3-3. 해시태그 AI 결과 표시
- 해시태그 mutation 결과를 AiSuggestionPanel로 표시
- `data.suggestions` 또는 `data.hashtags`에서 결과 추출하여 폼에 적용

---

## 4. 파일 변경 계획

### 4-1. 새로 생성하는 파일

| 파일 | 설명 |
|---|---|
| `features/contents/components/ContentInfoPanel.tsx` | 콘텐츠 정보 패널 (제목/본문/해시태그/예약) |
| `features/contents/components/SubtitlePanel.tsx` | 자막 편집 인라인 패널 (SubtitleEditorPage 리팩터링) |
| `features/contents/components/ShortformPanel.tsx` | 숏폼 추출 인라인 패널 (ShortformEditorPage 리팩터링) |
| `features/contents/components/EffectsPanel.tsx` | 효과음 패널 (신규) |
| `features/contents/components/EmojiPanel.tsx` | 이모지/스티커 패널 (신규) |
| `features/contents/components/AiAssistantPanel.tsx` | AI 어시스턴트 통합 패널 |
| `features/contents/components/PlatformSettingsPanel.tsx` | 플랫폼 설정 패널 (기존 코드 분리) |
| `features/contents/components/MediaMainArea.tsx` | 상단 미디어 영역 (VideoPlayer/이미지/업로드) |

### 4-2. 수정하는 파일

| 파일 | 변경 내용 |
|---|---|
| `features/contents/pages/ContentEditorPage.tsx` | 전면 재작성 — 레이아웃 재배치 + 패널 시스템 |
| `features/contents/components/SourceMediaSection.tsx` | MediaMainArea로 역할 이전, 간소화 또는 제거 |
| `features/contents/components/VariantEditor.tsx` | PlatformSettingsPanel 내부로 이동 |
| `features/contents/components/PlatformPreview.tsx` | 변경 없음 (재사용) |
| `features/ai/pages/SubtitleEditorPage.tsx` | SubtitlePanel import로 래퍼화 (기존 라우트 유지) |
| `features/ai/pages/ShortformEditorPage.tsx` | ShortformPanel import로 래퍼화 (기존 라우트 유지) |
| `app/router.tsx` | 변경 없음 (기존 라우트 유지, 양쪽 진입 가능) |
| `docs/사용자_가이드.md` | 부록 D/E 재작성 — 새 UI 기준 시나리오 |

### 4-3. 삭제/정리하는 항목

- ContentEditorPage 내 중복 AI 버튼 (인라인 extra 링크)
- ContentEditorPage 내 AiSuggestionPanel 직접 사용 (ContentInfoPanel로 이동)

---

## 5. 구현 순서

### Sprint 1: 기반 컴포넌트 분리 (ContentEditorPage 분해)
1. `ContentInfoPanel.tsx` 생성 — 기존 제목/본문/해시태그/예약 폼 추출
2. `AiAssistantPanel.tsx` 생성 — 기존 AI 어시스턴트 카드 + 모달들 추출
3. `PlatformSettingsPanel.tsx` 생성 — 플랫폼 선택/커스터마이즈/VariantEditor 추출
4. AI 버그 수정: `getContentText` 개선, 중복 버튼 제거, 해시태그 결과 표시

### Sprint 2: 영상 중심 레이아웃
5. `MediaMainArea.tsx` 생성 — VideoPlayer + WaveformViewer + 업로드 통합
6. ContentEditorPage 재작성 — Segmented 도구 바 + 패널 시스템
7. 미디어 타입 감지 로직 (영상→플레이어, 이미지→갤러리, 없음→업로드)

### Sprint 3: 자막/숏폼 인라인화
8. `SubtitlePanel.tsx` 생성 — SubtitleEditorPage에서 로직 추출
9. `ShortformPanel.tsx` 생성 — ShortformEditorPage에서 로직 추출
10. 기존 페이지들을 래퍼로 변환 (라우트 호환 유지)

### Sprint 4: 효과음/이모지 신규
11. `EffectsPanel.tsx` 생성 — AI 효과음 추천 + 수동 추가
12. `EmojiPanel.tsx` 생성 — AI 이모지 추천 + 수동 추가
13. 타임라인 데이터 구조 정의 (시점, 종류, 메타데이터)

### Sprint 5: 사용자 가이드 업데이트
14. 부록 D 재작성 — 새 UI 기준 영상 편집 시나리오
15. 부록 E 업데이트 — 플랫폼 설정 패널 기준
16. 섹션 5 (콘텐츠 관리) 스크린샷/설명 업데이트

---

## 6. 기존 라우트 호환

- `/ai/subtitle-editor/:assetId` — 유지 (SubtitlePanel을 전체 페이지로 래핑)
- `/ai/shortform-editor/:assetId` — 유지 (ShortformPanel을 전체 페이지로 래핑)
- `/contents/create` — ContentEditorPage (재설계 버전)
- `/contents/:id/edit` — ContentEditorPage (재설계 버전)
- 미디어 라이브러리에서의 진입 경로도 그대로 유지

---

## 7. 미디어 타입 적응 로직

```typescript
type MediaMode = 'video' | 'image' | 'empty';

function detectMediaMode(mediaUrls: string[]): MediaMode {
  if (mediaUrls.length === 0) return 'empty';
  const hasVideo = mediaUrls.some(url =>
    /\.(mp4|webm|mov)$/i.test(url) || url.includes('video')
  );
  return hasVideo ? 'video' : 'image';
}
```

- `video`: VideoPlayer + WaveformViewer + 영상 도구(자막/효과음/이모지/숏폼)
- `image`: 이미지 갤러리 뷰 + 이미지 도구(썸네일 생성만)
- `empty`: 업로드 드롭존 표시

---

## 8. 데이터 흐름

```
ContentEditorPage (Form 상태 관리)
  ├─ mediaUrls: string[]          → MediaMainArea
  ├─ title/body/hashtags          → ContentInfoPanel
  ├─ assetId (첫 번째 영상 URL)   → SubtitlePanel, ShortformPanel,
  │                                  EffectsPanel, EmojiPanel
  ├─ platforms/channels/variants  → PlatformSettingsPanel
  └─ AI mutations                 → AiAssistantPanel
```

- Form은 ContentEditorPage에서 관리 (현재와 동일)
- 각 패널은 props + callbacks로 데이터 주고받기
- 자막/숏폼/효과음/이모지는 콘텐츠 메타데이터에 저장

---

## 9. 사용자 가이드 업데이트 범위

### 부록 D 재작성 포인트
- 자막/숏폼이 별도 페이지가 아닌 콘텐츠 편집기 내 도구 바로 진입
- 효과음/이모지 시나리오 추가
- 워크플로우 다이어그램 갱신

### 부록 E 업데이트 포인트
- "플랫폼별 맞춤" 토글이 도구 바의 "플랫폼 설정" 패널로 이동
- 새 레이아웃 반영
