# 서비스에서 나온 기사 넣는 법

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
