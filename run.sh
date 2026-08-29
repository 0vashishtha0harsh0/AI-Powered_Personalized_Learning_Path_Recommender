#!/usr/bin/env bash
# ============================================================================
# PathAI — Run both backend (FastAPI) and frontend (Vite) together
# ============================================================================
# Usage:
#   ./run.sh              # start both servers
#   ./run.sh backend      # start only the backend
#   ./run.sh frontend     # start only the frontend
#
# Environment variables (optional):
#   GEMINI_API_KEY        Enable AI Mentor with Google Gemini (primary, supports comma-separated keys)
#   GROQ_API_KEY          Enable AI Mentor with Groq (fast free fallback)
#   OPENAI_API_KEY        Enable AI Mentor with OpenAI (fallback)
#   ANTHROPIC_API_KEY     Enable AI Mentor with Claude (fallback)
#   LLM_MODEL             Override model (default: gemini-2.0-flash)
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors and functions (defined early so .env loading can use them)
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}[PathAI]${NC} $*"; }
ok()    { echo -e "${GREEN}[PathAI]${NC} $*"; }
err()   { echo -e "${RED}[PathAI]${NC} $*" >&2; }

# Load .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    info "Loading .env file..."
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
VENV_DIR="$SCRIPT_DIR/.venv"

cleanup() {
    info "Shutting down..."
    kill "$BACKEND_PID" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
    wait "$FRONTEND_PID" 2>/dev/null || true
    ok "All servers stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

# --------------------------------------------------------------------------
# Install dependencies
# --------------------------------------------------------------------------
install_backend_deps() {
    info "Checking Python dependencies..."

    # Create virtualenv if it doesn't exist
    if [ ! -d "$VENV_DIR" ]; then
        info "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
        ok "Virtual environment created at $VENV_DIR"
    fi

    # Activate venv
    source "$VENV_DIR/bin/activate"

    # Install deps if fastapi is missing
    if ! python -c "import fastapi" 2>/dev/null; then
        info "Installing Python dependencies..."
        pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
        ok "Python dependencies installed."
    else
        ok "Python dependencies already installed."
    fi
}

install_frontend_deps() {
    info "Installing/checking Node dependencies..."
    (cd "$SCRIPT_DIR/frontend-part" && npm install --silent)
    ok "Node dependencies ready."

    # Fix vite binary permissions (fixes 'Permission denied' on Linux)
    chmod +x "$SCRIPT_DIR/frontend-part/node_modules/.bin/vite" 2>/dev/null || true
}

# --------------------------------------------------------------------------
# Start backend
# --------------------------------------------------------------------------
start_backend() {
    install_backend_deps

    # Activate venv for uvicorn
    source "$VENV_DIR/bin/activate"

    info "Starting backend on http://localhost:${BACKEND_PORT} ..."
    cd "$SCRIPT_DIR"
    uvicorn src.api.main:app \
        --host 0.0.0.0 \
        --port "$BACKEND_PORT" \
        --reload &
    BACKEND_PID=$!
    ok "Backend PID: $BACKEND_PID"
}

# --------------------------------------------------------------------------
# Start frontend
# --------------------------------------------------------------------------
start_frontend() {
    install_frontend_deps
    info "Starting frontend on http://localhost:${FRONTEND_PORT} ..."
    cd "$SCRIPT_DIR/frontend-part"
    npx vite --port "$FRONTEND_PORT" --host &
    FRONTEND_PID=$!
    ok "Frontend PID: $FRONTEND_PID"
}

# --------------------------------------------------------------------------
# Print banner
# --------------------------------------------------------------------------
print_banner() {
    echo ""
    echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║          🧠  PathAI  is running!             ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${GREEN}Backend${NC}   → http://localhost:${BACKEND_PORT}"
    echo -e "  ${GREEN}Frontend${NC}  → http://localhost:${FRONTEND_PORT}"
    echo -e "  ${GREEN}API Docs${NC}  → http://localhost:${BACKEND_PORT}/docs"
    echo ""
    if [ -n "$GEMINI_API_KEY" ]; then
        echo -e "  ${CYAN}AI Mentor${NC} → Gemini (${GEMINI_MODEL:-${LLM_MODEL:-gemini-2.0-flash}})"
    fi
    if [ -n "$GROQ_API_KEY" ]; then
        echo -e "  ${CYAN}AI Mentor${NC} → Groq (${GROQ_MODEL:-${LLM_MODEL:-openai/gpt-oss-20b}}) [fast fallback]"
    fi
    if [ -n "$OPENAI_API_KEY" ]; then
        echo -e "  ${CYAN}AI Mentor${NC} → OpenAI (${OPENAI_MODEL:-${LLM_MODEL:-gpt-4o-mini}})"
    fi
    if [ -n "$ANTHROPIC_API_KEY" ]; then
        echo -e "  ${CYAN}AI Mentor${NC} → Anthropic Claude"
    fi
    if [ -z "$GEMINI_API_KEY" ] && [ -z "$GROQ_API_KEY" ] && [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
        echo -e "  ${RED}AI Mentor${NC} → Not configured (set GEMINI_API_KEY or GROQ_API_KEY)"
    fi
    echo ""
    echo -e "  Press ${BOLD}Ctrl+C${NC} to stop all servers."
    echo ""
}

# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
MODE="${1:-all}"

case "$MODE" in
    backend)
        start_backend
        print_banner
        wait "$BACKEND_PID"
        ;;
    frontend)
        start_frontend
        print_banner
        wait "$FRONTEND_PID"
        ;;
    all|*)
        start_backend
        sleep 2
        start_frontend
        print_banner
        wait
        ;;
esac
