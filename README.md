# Agentic ASP Solver

LangGraph-driven multi-agent system that turns natural-language problem statements into Answer Set Programming (ASP) code, validates it with MCP tools, and iterates until correct.

## Overview

This project implements a multi-agent system that can:
- Convert natural language problem descriptions into ASP code
- Execute and validate the generated logic programs
- Iteratively refine solutions based on feedback
- Use MCP (Model Context Protocol) tools for enhanced capabilities

## Architecture at a glance

- Orchestrator: `ASPRunner` loads a problem, builds initial `ASPState`, opens an MCP session via `MCPClientManager`, compiles the graph, runs it, and exports results.
- Agents and control flow: `create_asp_system` builds two ReAct agents (solver with full MCP access; validator restricted to `solve_model` and `add_item`). `workflow.should_continue` loops solver→validator until validated or `max_iterations`.
- State: `ASPState` keys: `problem_description`, `asp_code`, `messages`, `validation_history`, `iteration_count`, `max_iterations`, `is_validated`, `answer_set`, `statistics`.
- LLM/MCP: `build_llm` config via env (Ollama-compatible OpenAI API by default). MCP tools loaded at runtime from a long-lived stdio session.

## Features

- **Multi-agent architecture**: Separate solver and validator agents
- **Natural language interface**: Describe problems in plain English
- **Iterative refinement**: Automatically improves solutions based on validation feedback
- **MCP integration**: Leverages external tools for enhanced problem-solving

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
cp .env.example .env
# Required for MCP (adjust absolute path after --directory):
MCP_SOLVER_COMMAND=uv
MCP_SOLVER_ARGS=--directory,absolute_path,run,mcp-solver-asp

# Ollama-friendly model defaults (override if needed):
MODEL_NAME=gpt-oss:20b
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
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

### LLM backend (Ollama)

- This project uses Ollama as the LLM backend by default (`http://localhost:11434/v1`). Ensure an Ollama server is running.
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
MODEL_NAME=gpt-oss:20b
# OPENAI_BASE_URL=http://localhost:11434/v1
# OPENAI_API_KEY=ollama
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

Note: Ensure your environment variables (e.g., `MODEL_NAME`, `OPENAI_BASE_URL`, `OPENAI_API_KEY`, and MCP settings like `MCP_SOLVER_ARGS`) are configured as described above before running the batch.

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

- Model 404s: the `MODEL_NAME` is not available on `OPENAI_BASE_URL` (pull or change the model).
- MCP "Connection closed": re-check `MCP_SOLVER_ARGS` absolute path after `--directory` and verify mcp-solver install.
- Validator skips if `asp_code` is empty: ensure the solver produced code before expecting a PASS.

