# databrew NOW — 비회원 댓글 운영

NOW 댓글은 GitHub/Meta 로그인 없이 닉네임으로 작성합니다. 스팸 방지를 위한 Cloudflare Turnstile, D1 데이터베이스, 관리자 승인 기능이 포함됩니다.

## 현재 준비된 것

- NOW 댓글 입력과 공개 댓글 목록 UI
- Cloudflare Worker/D1/Turnstile API (신규 댓글은 모두 승인 대기)
- [관리자 페이지](https://raspos.github.io/databrew/now/moderate/) — 토큰을 넣고 승인·반려·삭제
- [GitHub Actions 원클릭 배포](https://github.com/raspos/databrew/actions/workflows/deploy-guest-comments.yml) — Cloudflare에 로그인된 계정 인증정보를 GitHub Secret에 등록한 뒤 실행
- 외부 공유(Threads/X/Facebook/링크 복사)는 댓글 서비스 연결과 무관하게 계속 작동

## 처음 한 번만 필요한 설정 — GitHub Secrets 세 개

1. Cloudflare [대시보드](https://dash.cloudflare.com/)에서 로그인하고, 사용할 Account ID를 확인합니다. 기존 Cloudflare Pages를 관리하는 계정을 사용해도 됩니다.
2. [Cloudflare API 토큰 만들기](https://dash.cloudflare.com/profile/api-tokens)에서 전용 토큰을 만듭니다. 대상은 **사용할 Cloudflare 계정 하나**로 제한하고, 다음 권한을 부여합니다.
   - `Account → Workers Scripts → Edit` (Worker 배포)
   - `Account → D1 → Edit` (댓글 DB 생성·SQL 실행)
   - `Account → Turnstile → Edit` (스팸 방지 위젯 생성·조회)
   - Workers subdomain/account details를 조회하기 위한 읽기 권한이 추가로 요구되는 경우 해당 계정에만 부여합니다.
3. [databrew GitHub Actions Secrets](https://github.com/raspos/databrew/settings/secrets/actions)에서 아래 3개를 등록합니다. 절대 GitHub 파일·채팅·브라우저 댓글창에 인증정보를 입력하지 마세요.

| Secret 이름 | 값 |
|---|---|
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare 대시보드에서 확인한 32자리 Account ID |
| `CLOUDFLARE_API_TOKEN` | 방금 발급한 제한된 권한의 API 토큰 |
| `DATABREW_COMMENTS_ADMIN_TOKEN` | 본인이 만든 길이 32자 이상의 무작위 관리자 비밀번호. 관리자 페이지에 로그인 대신 입력할 값입니다. |

4. [Deploy databrew NOW guest comments](https://github.com/raspos/databrew/actions/workflows/deploy-guest-comments.yml)에 접속해 `Run workflow` → `main`을 선택해 실행합니다.

이 액션은 다음을 자동 수행합니다.

- Cloudflare에서 `databrew-now-comments`라는 전용 D1 DB를 찾거나 새로 생성
- `raspos.github.io`에만 허용된 Turnstile 위젯을 찾거나 생성
- 댓글 SQL 테이블 생성
- Worker 배포 및 개인 비밀값 3개를 Worker Secrets에 등록
- Cloudflare Worker에서 댓글 DB를 실제로 읽을 수 있는지 검사
- 성공할 때만 공개 주소와 공개 Turnstile Site Key를 `now/comments-config.json`에 기록해 GitHub Pages에 배포

별도로 D1 ID를 코드에 복사하거나 `wrangler` 명령어를 수동 실행할 필요가 없습니다. 이전에 같은 이름으로 만든 Cloudflare 리소스가 있다면 가능한 한 재사용하며, **기존 댓글을 지우는 자동 작업은 없습니다.**

**중요:** 이 저장소에 공개 코드를 추가했다고 곧바로 Cloudflare 계정에서 서버가 생성되지는 않습니다. 위 Secret 3개를 GitHub에 등록하고 배포 액션을 1회 실행해야 실제 서비스가 열립니다. 인증정보가 없으면 배포 액션은 시작 후 안전하게 중단됩니다.

## 댓글 승인·삭제

배포 후 [댓글 관리](https://raspos.github.io/databrew/now/moderate/)를 엽니다. GitHub 로그인은 필요 없고, 위에 등록한 `DATABREW_COMMENTS_ADMIN_TOKEN` 값을 직접 입력하면 됩니다. 읽기/승인/반려/영구 삭제가 가능하며, 토큰은 페이지의 메모리에서만 사용하고 저장하지 않습니다.

새 댓글은 기본적으로 `pending` 상태입니다. 승인하기 전에는 대중에게 보이지 않습니다.

## 보안과 운영 범위

- 독자에게 계정·실명·이메일을 요구하지 않습니다.
- 개인별 하루 12개/10분 3개 정도의 등록 제한, 익명 IP 해시, 금칙 입력 검사, Turnstile, 관리자 사전 승인을 사용합니다.
- 공개 댓글은 `nickname`, `content`, `created_at`만 읽을 수 있습니다. 관리자 API는 서버 측에서 Bearer 토큰으로 보호됩니다.
- API 토큰과 관리자 비밀값은 GitHub Actions Secrets에 저장하고, Cloudflare Worker에 비밀값으로 전달하며, 공개 GitHub Pages 파일에는 **공개 URL과 Site Key만** 저장합니다.
- 독자 댓글 저장에는 D1/Workers 사용량에 따른 요금제 제한이 적용됩니다. Cloudflare 계정의 사용량·요금 정책을 확인해 주세요.
- 지속 운영을 위해 댓글 보유기간, 개인정보 처리방침(해시 처리된 접속 정보 포함), 삭제 요청 절차를 정해야 합니다.
- 기존 공유 기능은 그대로 사용 가능합니다.

## 검증

```bash
cd comments-api
npm test
cd ..
python -m unittest discover -s tests -p 'test_now_engagement.py' -v
python -m unittest discover -s comments-api/tests -p 'test_provision.py' -v
```

현재 자동 검증은 로그인 없는 댓글 API와 승인, API 인증, Turnstile 검증 등을 모의 환경에서 검사합니다. 실제 방문자의 댓글 등록·승인 과정을 완전히 확인하려면 Cloudflare 계정 배포가 필요합니다.
