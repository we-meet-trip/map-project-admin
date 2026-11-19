# 0001. JSON API 서버와 별도 SPA

## 맥락
처음 콘솔은 FastAPI 가 Jinja2 템플릿으로 HTML 을 직접 그리는 읽기 전용 화면이었다([`9aa591a`](https://github.com/we-meet-trip/map-project-admin/commit/9aa591a649c504e555f24469b15f8172008ac3a6), [`3253c90`](https://github.com/we-meet-trip/map-project-admin/commit/3253c90e8e7cc4aaca445aa553268c61e5a70044)). 회원 조회·운영 액션·감사 조회를 더하면서 화면 상태(필터·페이지·확인 대화상자)와 권한별 버튼이 늘었다.

## 선택지
1. 서버 렌더 템플릿을 키운다.
2. admin 은 JSON API 만 내놓고 화면은 별도 SPA(React)로 만든다.

## 결정
두 번째를 택했다. admin 은 `/api/v1` JSON API 만 제공하고(HTML 없음), 화면은 `web/` 의 React SPA 가 같은 출처의 nginx 뒤에서 `/api/` 를 admin 으로 넘긴다([`53e1d4c`](https://github.com/we-meet-trip/map-project-admin/commit/53e1d4cceab5c093d0a3a90384282e355bd2621f)).

## 결과
- API 와 화면을 따로 시험할 수 있다(pytest / tsc·vite 빌드).
- 같은 출처라 세션 쿠키를 SameSite=Lax 로 둘 수 있다. 개발 서버(Vite)에서만 CORS 가 필요하다.
- 화면 빌드가 하나 더 생겼다(Node 툴체인).
