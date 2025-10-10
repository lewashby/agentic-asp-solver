# Agentic ASP Solver

A lightweight ASP (Answer Set Programming) coding agent that generates, runs, and refines logic programs through natural language instructions using LangGraph.

## Overview

This project implements a multi-agent system that can:
- Convert natural language problem descriptions into ASP code
- Execute and validate the generated logic programs
- Iteratively refine solutions based on feedback
- Use MCP (Model Context Protocol) tools for enhanced capabilities

## Features

- **Multi-agent architecture**: Separate solver and validator agents
- **Natural language interface**: Describe problems in plain English
- **Iterative refinement**: Automatically improves solutions based on validation feedback
- **MCP integration**: Leverages external tools for enhanced problem-solving
- **LangGraph Studio support**: Visual debugging and development

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
# Add your OpenAI API key and MCP Solver configuration
# IMPORTANT!!!
# Update the .env variable MCP_SOLVER_ARGS with the MCP Solver absolute path
# MCP_SOLVER_ARGS=--directory,MCP_SOLVER_PATH,run,mcp-solver-asp
```

**Run**:

```bash
asper -h
```

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
# OPENAI_BASE_URL and OPENAI_API_KEY can be left at defaults for Ollama
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

## Project Structure

- `src/asper/` - Core agent implementation
- `examples/` - Sample problems and use cases
- `prompts/` - System prompts for different agent roles
- `tests/` - Unit and integration tests

## Development

The system uses LangGraph for orchestration and supports hot reload during development. Check out the [LangGraph documentation](https://langchain-ai.github.io/langgraph/) for more advanced features.

