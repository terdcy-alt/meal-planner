#!/bin/bash
# Start both backend and frontend in development mode

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== Starting Meal Planner ==="

# Backend
echo ""
echo "Starting FastAPI backend on http://localhost:8000 ..."
cd "$ROOT/backend"

if [ ! -f .env ]; then
  echo "WARNING: backend/.env not found. Copy .env.example and add your ANTHROPIC_API_KEY."
fi

if [ ! -d venv ]; then
  echo "Creating Python virtual environment..."
  /usr/bin/python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# Frontend
echo "Starting Next.js frontend on http://localhost:3000 ..."
cd "$ROOT/frontend"

if [ ! -f .env.local ]; then
  cp .env.local.example .env.local
fi

npm install --silent
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✓ Backend:  http://localhost:8000"
echo "✓ Frontend: http://localhost:3000"
echo "✓ API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

wait $BACKEND_PID $FRONTEND_PID
