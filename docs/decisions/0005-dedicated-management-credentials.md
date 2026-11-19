# 0005. 관리 호출에 전용 자격

## 맥락
서비스 사이의 일반 내부 토큰 하나로 회원 관리와 허브 관리 API 를 모두 부를 수 있었다. 그 토큰을 가진 다른 서비스가 관리자 행위자를 꾸밀 수 있었다.

## 선택지
1. 일반 내부 토큰을 계속 쓴다.
2. 관리 호출에만 서비스별 전용 토큰을 쓴다.
3. mTLS

## 결정
서비스별 전용 토큰(`MAP_PROJECT_USER_ADMIN_INTERNAL_TOKEN`, `MAP_PROJECT_HUB_ADMIN_INTERNAL_TOKEN`)을 택했다. 비었거나 일반 토큰·다른 관리 토큰과 같으면 네트워크 요청 전에 막고, 선택한 대상의 정해진 경로에만 붙이며 리다이렉트를 따라가지 않는다([`b42c361`](https://github.com/we-meet-trip/map-project-admin/commit/b42c361526c7736cfdf3aff0769afd94a141caad), [`454b8af`](https://github.com/we-meet-trip/map-project-admin/commit/454b8af9ccee72d2dfad19ebe81e8a2d845d52b7)).

## 결과
- 일반 토큰이 새어도 관리 API 는 열리지 않는다.
- 비밀이 둘 늘었고, 받는 서비스(user·hub)도 같은 전용 토큰을 요구해야 한다.
- mTLS 는 쓰지 않는다. 위임 호출에는 대상별 클라이언트 인증서 설정이 없다.
