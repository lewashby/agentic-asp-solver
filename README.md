# Agentic ASP Solver

LangGraph-driven multi-agent system that turns natural-language problem statements into Answer Set Programming (ASP) code, validates it with MCP tools, and iterates until correct.

## Overview

This project implements a multi-agent system that can:
- Convert natural language problem descriptions into ASP code
- Execute and validate the generated logic programs
- Iteratively refine solutions based on feedback
- Use MCP (Model Context Protocol) tools for enhanced capabilities

## Architecture
- Orchestrator: `ASPRunner` loads a problem, builds initial `ASPState`, opens an MCP session via `MCPClientManager`, compiles the graph, runs it, and exports results.
- Agents and control flow: `create_asp_system` builds two ReAct agents (solver with full MCP access; validator restricted to `solve_model` and `add_item`). `workflow.should_continue` loops solver→validator until validated or `max_iterations`.
- State: `ASPState` keys: `problem_description`, `asp_code`, `messages`, `validation_history`, `iteration_count`, `max_iterations`, `is_validated`, `answer_set`, `statistics`.
- LLM/MCP: `build_llm` config via env (Ollama-compatible OpenAI API by default). MCP tools loaded at runtime from a long-lived stdio session.

## Features

- **Multi-agent architecture**: Separate solver and validator agents
- **Natural language interface**: Describe problems in plain English
- **Iterative refinement**: Automatically improves solutions based on validation feedback
- **MCP integration**: Leverages external tools for enhanced problem-solving
- **Web Interface**: Interactive Streamlit-based UI for testing and experimentation

## Quick Start

[Install uv](https://docs.astral.sh/uv/getting-started/installation/)

**Install dependencies**:

```bash
uv sync
uv pip install -e .
```

**Install MCP Solver**:

```bash
# Clone the MCP Solver repository
git clone https://github.com/szeider/mcp-solver.git
cd mcp-solver
uv sync
source .venv/bin/activate
uv pip install -e ".[asp]"  # Install asp solver 
# Check the installation instructions in the MCP Solver README
```

**Set up environment**:

```bash
# Chat Model Configuration
PROVIDER=ollama  # 'openrouter' or 'ollama'
MODEL_NAME=gpt-oss:20b
PROVIDER_BASE_URL=http://localhost:11434/v1
PROVIDER_API_KEY=ollama
TEMPERATURE=0.0

# Reasoning Configuration (for reasoning models)
# Can be: low, medium, high, true, or false
REASONING_LEVEL=false

# MCP Solver Configuration
MCP_SOLVER_ARGS=--directory,absolute_path_to_folder,run,mcp-solver-asp
MCP_SOLVER_COMMAND=uv
MCP_SOLVER_TRANSPORT=stdio

# Langsmith Configuration
LANGSMITH_API_KEY=kjbxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LANGSMITH_TRACING=false

# General Configuration
MAX_ITERATIONS=5
LOG_LEVEL=INFO
EXPORT_PATH=results
```

**Run**:

```bash
asper -h
# Single run example:
asper .\examples\graph_coloring.md
```

### Outputs

- Results exported to `results/...` (`.json` and generated `.lp`).
- Logs written to `results/....log`.

## Web Interface

Run with Docker (no local installs):
```bash
cp .env.example .env  # optional overrides
# Edit .env if needed:
# MODEL_NAME=gpt-oss:20b
# PROVIDER_BASE_URL=http://host.docker.internal:11434/v1
# PROVIDER_API_KEY=ollama

docker compose up --build
```

Open:
- http://localhost:8501

Stop:
```bash
docker compose down
```

Notes:
- Uses host.docker.internal to reach the host LLM; see “LLM backend (Ollama or OpenRouter)” for setup
- MCP Solver is preinstalled in the image; no host install needed

Run locally (optional, if you installed dependencies):
```bash
asper-webapp
```

#### Using an external Ollama via SSH tunneling
If your Ollama server runs on a remote machine (not on the Docker host), you can create an SSH tunnel from inside the container so the app can access it at http://localhost:11434/v1:

1) Ensure SSH access to the remote host (key-based auth recommended).
2) Provide SSH keys to the container (uncomment and adjust in docker-compose.yml):
```yaml
# volumes:
#   - ~/.ssh:/root/.ssh:ro
#   # Windows example:
#   # - C:/Users/<you>/.ssh:/root/.ssh:ro
```
3) Set the following environment variables (in your .env or compose environment):
```bash
# Enable the tunnel and set remote destination
OLLAMA_TUNNEL_ENABLE=true
OLLAMA_SSH_HOST=remote.example.com
OLLAMA_SSH_USER=youruser
# Optional ports (defaults shown)
OLLAMA_LOCAL_PORT=11434
OLLAMA_REMOTE_PORT=11434
# Use the tunneled endpoint inside the container
PROVIDER_BASE_URL=http://localhost:11434/v1
```
4) Start the stack:
```bash
docker compose up --build
```
The entrypoint will open an SSH local port-forward to the remote Ollama and route LLM traffic through it.

#### Web App Features
- Problem Description: Enter your ASP problem in natural language
- Custom Prompts: Override default solver and validator system prompts
- Live Logging: Watch the agent’s reasoning process in real-time
- Results Viewer: See generated ASP code and JSON results
- Stop Control: Interrupt long-running executions
- Configuration: Adjust model, temperature, iterations, and more

### LLM backend (Ollama or OpenRouter)

Ollama (local):
- This project uses Ollama as the LLM backend by default. Ensure an Ollama server is running.
- Install Ollama from `https://ollama.com` and start the server (on most systems it runs automatically). To start manually:
```bash
ollama serve
```
- Pull or choose a local model:
```bash
ollama pull gpt-oss:20b
```
- Optionally set the model via `.env`:
```bash
PROVIDER=ollama
MODEL_NAME=gpt-oss:20b
# PROVIDER_BASE_URL=http://localhost:11434/v1
# PROVIDER_API_KEY=ollama
```

OpenRouter:
- Set the provider to OpenRouter via environment variables:
```bash
# .env or docker-compose environment
PROVIDER=openrouter
MODEL_NAME=openai/gpt-5   # or any model from https://openrouter.ai/models
PROVIDER_BASE_URL=https://openrouter.ai/api/v1
PROVIDER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxx
```

## Examples

### Birds Fly

- A small knowledge base about birds, exceptions (penguins, injuries), and derived properties (mobility, feathers). Determine which entities can fly, are mobile, and have feathers, and cite whether each conclusion comes from a default, an exception, or a direct fact.

Run:

```bash
asper .\examples\birds_fly.md
```

### Graph Coloring

- A 4-node graph with specified edges. Find a valid 3-coloring such that adjacent nodes have different colors.

Run:

```bash
asper .\examples\graph_coloring.md
```

## LPCP Problems

### Download LPCP problem statements

Use the built-in scraper to download LPCP problem descriptions (defaults to years 2020–2025) into the `lpcp_problems/` folder:

```bash
download-lpcp
```

This will create a structure like:

```
lpcp_problems/
  lpcp-2020/
    problem-1.md
    problem-2.md
    ...
  lpcp-2021/
  ...
```

### Run asper across all LPCP problems

After downloading, run the batch executor to solve each problem file. By default it scans `lpcp_problems/` and processes `problem-1.md` and `problem-2.md` in each year folder:

```bash
asper-batch
```

Common options:

- `--root PATH`: root folder with `lpcp-YYYY` subfolders (default: `lpcp_problems`)
- `--years 2022,2023`: restrict to specific years (comma-separated)
- `--solver-prompt PATH`: custom solver system prompt file
- `--validator-prompt PATH`: custom validator system prompt file
- `--model NAME`: LLM model override (otherwise uses `MODEL_NAME` env or default)
- `--max-iterations N`: max solver/validator iterations

Examples:

```bash
# Run only for 2022 and 2023
asper-batch --years 2022,2023

# Use custom prompts
asper-batch \
  --solver-prompt prompts/solver_instructions.md \
  --validator-prompt prompts/validator_instructions.md

# Override model and iterations
asper-batch --model gpt-oss:20b --max-iterations 6
```

Note: Ensure your environment variables (e.g., `MODEL_NAME`, `PROVIDER_BASE_URL`, `PROVIDER_API_KEY`, and MCP settings like `MCP_SOLVER_ARGS`) are configured as described above before running the batch.

## Project Structure

- `src/asper/` - Core agent implementation
- `examples/` - Sample problems and use cases
- `prompts/` - System prompts for different agent roles
- `tests/` - Tests

## Development

The system uses LangGraph for orchestration and supports hot reload during development. Check out the LangGraph docs for more.

```bash
# Tests
pytest
```

## Troubleshooting

- Model 404s: the `MODEL_NAME` is not available on `PROVIDER_BASE_URL` (pull or change the model).
- MCP "Connection closed": re-check `MCP_SOLVER_ARGS` absolute path after `--directory` and verify mcp-solver install.
- Validator skips if `asp_code` is empty: ensure the solver produced code before expecting a PASS.

