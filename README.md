PartyGame - Kahoot + Slido clone (open-source starter)

This archive contains a ready-to-deploy project combining realtime quizzes (timed), polls, and Q&A.

Folders:
- backend/: FastAPI + python-socketio backend. Dockerfile included.
- frontend/: Vite + React frontend.

Quick local run (without Docker):
- Backend:
  $ python3 -m venv .venv
  $ source .venv/bin/activate
  $ pip install -r backend/requirements.txt
  $ cd backend
  $ uvicorn app.main:sio_app --reload --host 0.0.0.0 --port 8000

- Frontend:
  $ cd frontend
  $ npm install
  $ npm run dev
  Open http://localhost:5173

Deploy notes:
- Use MongoDB Atlas for MONGO_URI and set it in backend environment.
- Deploy backend to Render (Docker or Web Service) and frontend to Vercel (set VITE_API_URL).
- See the earlier conversation for detailed Render & Vercel steps.

