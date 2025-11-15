#!/bin/bash
set -e

# Activate uv environment
source .venv/bin/activate

# Export MCP_SOLVER_COMMAND and MCP_SOLVER_ARGS if not set
export MCP_SOLVER_COMMAND=${MCP_SOLVER_COMMAND:-uv}
export MCP_SOLVER_ARGS=${MCP_SOLVER_ARGS:-"--directory,/mcp-solver,run,mcp-solver-asp"}

# Export other environment variables with defaults
export MODEL_NAME=${MODEL_NAME:-gpt-oss:20b}
export PROVIDER_BASE_URL=${PROVIDER_BASE_URL:-http://host.docker.internal:11434/v1}
export PROVIDER_API_KEY=${PROVIDER_API_KEY:-ollama}

# Run the command
if [ "$1" = "webapp" ]; then
    exec asper-webapp --server.address=0.0.0.0
elif [ "$1" = "batch" ]; then
    exec asper-batch "${@:2}"
elif [ "$1" = "download-lpcp" ]; then
    exec download-lpcp "${@:2}"
else
    exec asper "$@"
fi