# PathAI Frontend

React + TypeScript prototype for an AI-powered personalized learning path.

## Run

```bash
npm install
npm run dev
```

## Backend integration

All current data is isolated in `src/data/mock.ts`.

Replace those mock objects with API calls. Recommended endpoints:

- `GET /api/profile`
- `GET /api/recommendations`
- `GET /api/learning-path`
- `GET /api/skills`
- `GET /api/progress`
- `POST /api/feedback`
- `POST /api/chat`

Keep the component shapes unchanged where possible. This keeps the UI layer
independent from the ML implementation.

## Important

The recommendation score, course index, explanation and path order should come
from your existing backend. The frontend only renders those results.
