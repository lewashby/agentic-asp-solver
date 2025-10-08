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

1. **Install dependencies**:
```bash
uv sync
```

2. **Install MCP Solver**:
```bash
# Clone the MCP Solver repository
git clone https://github.com/szeider/mcp-solver.git
cd mcp-solver
uv sync
source .venv/bin/activate
uv pip install -e ".[asp]"  # Install asp solver 
# Check the installation instructions in the MCP Solver README
```

3. **Set up environment**:
```bash
cp .env.example .env
# Add your OpenAI API key and MCP Solver configuration
```

4. **Start the server**:
```bash
langgraph dev
```

5. **Run**:
```bash
uv run python .\src\asper\main.py
```

## Example

Try the birds flying problem in `examples/birds_fly.md` - describe which entities can fly, are mobile, and have feathers based on the given rules and exceptions.

## Project Structure

- `src/asper/` - Core agent implementation
- `examples/` - Sample problems and use cases
- `prompts/` - System prompts for different agent roles
- `tests/` - Unit and integration tests

## Development

The system uses LangGraph for orchestration and supports hot reload during development. Check out the [LangGraph documentation](https://langchain-ai.github.io/langgraph/) for more advanced features.

