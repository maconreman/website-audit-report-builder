#!/bin/bash
# ==============================================
#  Website Audit Report Builder — Start Script
#  Launches both backend (Flask) and frontend (Vite)
# ==============================================

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=============================================="
echo "  Website Audit Report Builder"
echo "=============================================="
echo ""

# --- Backend ---
echo "▸ Starting Flask backend on http://localhost:5000 ..."
cd "$ROOT_DIR"
python run.py &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

# Wait for backend to be ready
sleep 2

# --- Frontend ---
echo ""
echo "▸ Starting Vite frontend on http://localhost:5173 ..."
cd "$ROOT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"

echo ""
echo "=============================================="
echo "  Backend:  http://localhost:5000"
echo "  Frontend: http://localhost:5173  ← open this"
echo "=============================================="
echo ""
echo "Press Ctrl+C to stop both servers."
echo ""

# Cleanup on exit
cleanup() {
  echo ""
  echo "Shutting down..."
  kill $BACKEND_PID 2>/dev/null
  kill $FRONTEND_PID 2>/dev/null
  echo "Done."
}
trap cleanup EXIT INT TERM

# Wait for either process to exit
wait
