# STORIES 기사 넣는 법

허브 맨 위 프로젝트 검색 바로 위에 `articles.json`의 기사가 최신순으로 최대 5개 표시됩니다.
기사가 하나도 없으면 영역 전체가 숨겨집니다. 6개 이상 적어 두면 날짜가 가장 최근인 5개만 보입니다.

## 형식

```json
[
  {
    "title": "기사 제목",
    "url": "https://기사-주소",
    "outlet": "언론사 또는 매체",
    "date": "2026-11-19",
    "project": "bokwatch",
    "summary": "한 줄 설명(선택)",
    "en": { "title": "English title", "outlet": "Outlet", "summary": "One-line summary" }
  }
]
```

- 필수: `title`, `url`(http/https). 나머지는 선택입니다.
- `project`: 기사가 나온 서비스의 폴더 이름(예: `bokwatch`, `fx-odds`, `bok-governor`). 넣으면 그 프로젝트 상세 페이지로 가는 칩이 붙습니다.
- `en`: 영어 허브에 보일 제목·매체·설명입니다. 없으면 한국어 값을 그대로 씁니다.
- `date`: `YYYY-MM-DD`. 정렬 기준입니다.

## 넣는 방법

1. 대화에서 "이 기사 넣어줘 + 주소"라고 하면 제가 형식에 맞춰 넣고 배포합니다.
2. 직접 하려면 GitHub에서 `articles.json`을 열어 연필 아이콘으로 편집하고 커밋하면 1~2분 뒤 반영됩니다.

## 글쓰기 도구(CMS)

`/databrew/admin/` 에서 브라우저로 직접 쓰고 올릴 수 있습니다. 본문 작성, 사진 올리기, 링크 걸기, 말머리 만들기를 지원하고, 올리면 GitHub에 바로 커밋됩니다.
처음 한 번 GitHub 토큰(저장소 raspos/databrew, Contents 읽기·쓰기 권한만)을 넣으면 이 브라우저에 기억합니다.

- 말머리: 제목 앞에 `[BOK워치]` 형태로 붙습니다. "서비스 이름 자동"이면 선택한 서비스 이름이 되고(영어 허브에서는 영어 이름), 아니면 직접 쓴 글자(`tag`)가 됩니다.
- 직접 쓴 기사는 `articles/<id>/`에 페이지와 사진, 원본(`source.md`)으로 저장되고 `articles.json`에는 `url: "articles/<id>/"`로 등록됩니다.

## 조회수

- 모든 페이지(허브, 상세, 기사)가 `analytics.js`로 페이지별 조회수를 셉니다. 같은 탭에서 같은 페이지를 다시 열어도 한 번만 세고, 배포 주소가 아닌 곳(로컬 테스트)에서는 올리지 않습니다.
- 글쓰기 도구의 "조회수 보기"에서 페이지별 조회수와 사이트 누적 방문을 한 번에 볼 수 있습니다. 직접 쓴 기사 페이지에는 조회수가 함께 표시됩니다.
- GoatCounter도 함께 쓰려면 `analytics.js` 맨 위의 `GC_CODE`에 사이트 코드를 넣으세요(PAY워치처럼 쿠키 없이 방문 통계를 따로 봅니다). 지금은 꺼져 있습니다.

## 댓글 (giscus)

기사 페이지(`/articles/<id>/`) 맨 아래에 댓글이 붙도록 `comments.js`가 준비돼 있습니다. GitHub Discussions를 쓰는 giscus 방식이고, 기사마다 고정 ID(`article-<id>`)로 토론이 하나씩 연결되므로 기사를 수정해 다시 게시해도 댓글이 유지됩니다. 기존에 올린 기사에도 자동으로 붙습니다.
아직 저장소에서 Discussions가 꺼져 있고 giscus 앱이 설치되지 않아, **아래 설정을 마치기 전에는 댓글 영역이 보이지 않습니다**(기사 읽기에는 영향 없음).

1. 저장소 `raspos/databrew` → Settings → General → Features → **Discussions** 체크
2. Discussions 탭에서 카테고리 하나 만들기(이름 예: `댓글`, 형식은 **Announcements** 권장: 새 토론은 관리자와 giscus만 만들 수 있어 스팸이 줄어듭니다)
3. https://github.com/apps/giscus 에서 **Install** → `raspos/databrew` 선택
4. https://giscus.app 에서 저장소 `raspos/databrew`와 위 카테고리를 고르면 화면 아래 코드에 `data-category-id="DIC_…"` 값이 나옵니다. 그 값을 `comments.js`의 `categoryId`에 넣으면 됩니다(저에게 알려 주셔도 됩니다). `repoId`(`R_kgDOVUoIRA`)는 이미 들어 있습니다.

- 댓글 작성은 GitHub 로그인이 필요합니다. 읽기는 로그인 없이 됩니다. GitHub 계정이 없는 독자도 쓰게 하려면 별도 인증·저장 시스템이 필요해 이번 범위에는 넣지 않았습니다.
- 삭제·숨김·차단은 저장소 Discussions 화면에서 관리자가 합니다.
- 댓글 서비스가 응답하지 않으면 "댓글을 불러오지 못했습니다" 안내만 나오고 기사는 그대로 보입니다.
