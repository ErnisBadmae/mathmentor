#!/bin/sh
# Names graphify communities using a local OpenAI-compatible LLM instead of a
# cloud API key. Reads LLAMA_CPP_BASE_URL/API_KEY/MODEL (falls back to
# VLLM_BASE_URL/API_KEY/MODEL) from .env at the repo root and maps them onto
# OPENAI_BASE_URL/API_KEY/MODEL, which graphify's `--backend openai` understands
# (it also reaches llama.cpp/vLLM/LM Studio servers, not just OpenAI itself).
#
# Called from the post-commit hook's detached rebuild process, after the
# AST-only rebuild has finished writing graph.json - never run concurrently
# with the rebuild, or the label step can read a half-written graph.
#
# Usage: graphify_label_local.sh <repo_root> <graphify_python>
set -eu

REPO_ROOT="${1:-.}"
GRAPHIFY_PYTHON="${2:-}"
ENV_FILE="$REPO_ROOT/.env"

_val() {
    [ -f "$ENV_FILE" ] && grep -m1 "^$1=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | tr -d '\r'
}

if [ -z "${OPENAI_BASE_URL:-}" ]; then
    _base=$(_val LLAMA_CPP_BASE_URL); [ -z "$_base" ] && _base=$(_val VLLM_BASE_URL)
    _key=$(_val LLAMA_CPP_API_KEY);  [ -z "$_key" ]  && _key=$(_val VLLM_API_KEY)
    _model=$(_val LLAMA_CPP_MODEL);  [ -z "$_model" ] && _model=$(_val VLLM_MODEL)
    if [ -n "$_base" ]; then
        export OPENAI_BASE_URL="$_base"
        [ -n "$_key" ] && export OPENAI_API_KEY="$_key"
        [ -n "$_model" ] && export OPENAI_MODEL="$_model"
    fi
fi

if [ -z "${OPENAI_BASE_URL:-}" ]; then
    echo "[graphify label] no local LLM configured (set LLAMA_CPP_BASE_URL or VLLM_BASE_URL in .env) - skipping." >&2
    exit 0
fi

if [ -z "$GRAPHIFY_PYTHON" ] || ! "$GRAPHIFY_PYTHON" -c "import graphify" 2>/dev/null; then
    echo "[graphify label] graphify python not found - skipping." >&2
    exit 0
fi

if ! "$GRAPHIFY_PYTHON" -c "import openai" 2>/dev/null; then
    echo "[graphify label] 'openai' package missing in graphify's Python - install it: $GRAPHIFY_PYTHON -m pip install openai" >&2
    exit 0
fi

cd "$REPO_ROOT"
echo "[graphify label] naming communities via $OPENAI_BASE_URL (${OPENAI_MODEL:-default model})..."
if [ -n "${OPENAI_MODEL:-}" ]; then
    "$GRAPHIFY_PYTHON" -m graphify label . --backend openai --model "$OPENAI_MODEL" \
        || echo "[graphify label] labeling failed - communities may stay as placeholders." >&2
else
    "$GRAPHIFY_PYTHON" -m graphify label . --backend openai \
        || echo "[graphify label] labeling failed - communities may stay as placeholders." >&2
fi
