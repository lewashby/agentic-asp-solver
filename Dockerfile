FROM python:3.12-slim

# Install system dependencies including clingo
RUN apt-get update && apt-get install -y --no-install-recommends\
    git \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Clone and install MCP Solver dependency
RUN git clone https://github.com/szeider/mcp-solver.git /mcp-solver && \
    cd /mcp-solver && \
    uv sync && \
    uv pip install ".[asp]"

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY prompts/ ./prompts/

# Install project dependencies
RUN uv sync

# Install project dependencies
RUN uv pip install .

# Expose Streamlit port
EXPOSE 8501

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command runs the webapp
CMD ["webapp"]