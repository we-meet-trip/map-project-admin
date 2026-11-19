# 0002. 공유 HTTP Basic 대신 계정·서버측 세션

## 맥락
처음에는 운영자 모두가 비밀번호 하나를 나눠 쓰는 HTTP Basic 이었다. 그러면 감사 기록에 누가 했는지가 남지 않고, 한 사람을 막으려면 모두의 비밀번호를 바꿔야 한다.

## 선택지
1. 공유 Basic 유지
2. 계정별 비밀번호 + 서버측 세션(HttpOnly 쿠키)
3. 외부 IdP(OIDC) 연동

## 결정
계정별 bcrypt 비밀번호와 서버측 세션을 택했다(`admin_accounts`, `admin_sessions`). 세션은 Redis 논리 DB 를 새로 쓰지 않고 control DB 테이블에 둔다. 최초 계정은 계정이 하나도 없을 때만 `ADMIN_BOOTSTRAP_USER`·`ADMIN_BOOTSTRAP_PASSWORD` 로 만든다. 뒤에 역할(owner·operator·viewer)과 허용 환경, DB 공유 로그인 시도 제한을 더했다({{commit:7e30690}}).

## 결과
- 감사 기록의 행위자가 사람 단위가 된다.
- 외부 IdP 가 없어도 돈다. 대신 비밀번호 관리 책임이 콘솔에 있다.
- 세션 쿠키는 기본 Secure 다. http 로 띄우는 로컬 실행에서만 끈다.
