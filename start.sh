#!/bin/bash
echo "========================================"
echo "  AI Daily - One-click Start"
echo "========================================"

cd "$(dirname "$0")"

# Start API
echo "[Start] FastAPI..."
uvicorn api.main:app --port 8000 &
API_PID=$!
sleep 3

# Start frontend
echo "[Start] Frontend..."
cd frontend
npx vite --port 5173 &
FE_PID=$!
cd ..

sleep 5
echo "[Open] Browser..."
start http://localhost:5173 2>/dev/null || xdg-open http://localhost:5173 2>/dev/null || echo "http://localhost:5173"

echo ""
echo "  Frontend : http://localhost:5173"
echo "  API      : http://localhost:8000"
echo "========================================"

wait
