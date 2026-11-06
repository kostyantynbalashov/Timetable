# Frontend (React + Vite + TypeScript)

```bash
npm install
npm run dev     # http://localhost:5173, expects backend on :8000 (see .env.development)
```

Pages: `Викладачі` / `Аудиторії` / `Групи` (CRUD) · `Імпорт Excel` (operator
bulk entry) · `Навантаження` (workload) · `Розклад` (read-only view by
group/teacher — department-head and room views exist as API endpoints,
not yet wired into the UI).

No build step for production yet (`npm run build` works but nothing serves
the static bundle) — add once there's a deployment target.
