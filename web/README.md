# MAP 운영 콘솔 화면 (map-project-admin-web)

운영자용 관리 콘솔 SPA. 같은 저장소의 admin JSON API(`map_project_admin/`)를 쓰는 읽기 우선 화면이며, 모든 쓰기 액션은 확인 대화상자를 거치고 서버 쪽 감사 로그에 남는다.

## 기술 스택
판 번호는 `package.json` 이 기준이다(모두 고정 판).

- React 18 + TypeScript(strict)
- Vite(빌드·개발 서버)
- React Router(`createBrowserRouter`)
- TanStack Query(데이터 가져오기·캐시)
- Tailwind CSS(PostCSS + autoprefixer)
- Recharts(개요 차트)

외부 아이콘·UI 라이브러리 없이 인라인 SVG 와 자체 컴포넌트로 만든다.

## 개발
```bash
npm ci
npm run dev
```
- 개발 서버: <http://localhost:5173>
- `/api` 요청은 `vite.config.ts` 의 프록시가 로컬 admin API(`http://127.0.0.1:8002`)로 넘긴다.
- admin API 를 함께 띄워야 로그인과 데이터 호출이 된다. 화면은 상대 경로 `/api` 로 요청하고 개발 서버가 이를 프록시하므로 브라우저 입장에서는 같은 출처다 — CORS 설정은 필요 없다. http 로 띄우므로 admin `.env` 에 `ADMIN_SESSION_COOKIE_SECURE=false`(로컬 실행용)가 필요하다.

## 빌드
```bash
npm run build      # tsc 타입 검사 후 vite 빌드 → dist/
npm run preview    # 빌드 결과 미리보기(:5173)
npm run typecheck  # 타입 검사만
```

## 컨테이너로 서빙
nginx 가 정적 빌드를 서빙하고, 같은 출처의 `/api/` 를 admin 컨테이너(`admin:8000`)로 넘긴다. 세션 쿠키(`admin_session`, HttpOnly)는 같은 출처라 그대로 오간다.

```bash
docker build -t map-project-admin-web .
```
- `Dockerfile`: `node:22-alpine` 에서 `npm ci && npm run build` → `nginx:alpine` 에 `dist/` 와 `nginx.conf` 복사(멀티아치 베이스라 amd64·arm64 에서 빌드된다).
- `nginx.conf`: `location /api/` → `http://admin:8000`, `location /` → `try_files $uri /index.html`(SPA 폴백). `/metrics` 같은 admin 의 다른 경로는 넘기지 않는다.
- 함께 띄우는 compose 구성은 [map-project-infra](https://github.com/we-meet-trip/map-project-infra) 에 있다.

## 인증 흐름
- 모든 요청은 `credentials: 'include'` 로 세션 쿠키를 보내고, 고른 환경을 `X-Map-Environment` 헤더로 보낸다.
- 처음 열 때 `GET /api/v1/auth/me` 로 세션을 확인한다. 401 이면 `/login` 으로 간다.
- 어느 요청이든 401 이 오면 세션을 비우고 `/login` 으로 보낸다. 403 은 화면을 깨지 않고 오류 배너로 보여 준다.

## 구조
```
src/
  api/                 client(fetch 래퍼) · endpoints · types
  app/                 router · RootLayout · RequireAuth · nav
  components/          재사용 UI(DataTable, StatTile, StatusPill, Modal 등)
  components/layout/   AppLayout · Sidebar · TopBar
  providers/           Auth · Theme · Toast · Confirm(확인 대화상자)
  pages/               Overview · External · Weather · Places · Users · Jobs · Db · Audit ·
                       Monitoring · Operators · Moderation · Login · NotFound
  lib/                 format · status · cn
```

## 디자인
- 라이트 우선 + 자동 다크(`prefers-color-scheme`) + 수동 토글(`data-theme`, localStorage `map-admin-theme`).
- 상태 색(정상·주의·경고·중단)은 늘 텍스트 라벨이나 아이콘과 함께 쓴다(색만으로 구분하지 않는다).
- 신고 원문은 React 이스케이프로만 그리고, 브라우저 저장소에 두지 않으며, 상세를 닫으면 캐시에서 지운다.
