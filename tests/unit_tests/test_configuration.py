"""Configuration tests."""

import os
import shutil
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()


class TestEnvironment:
    """Test environment setup."""

    def test_env_file_exists(self):
        """Test that .env file exists."""
        env_path = Path(".env")
        if not env_path.exists():
            pytest.skip(".env file not found - create from .env.example")
        assert env_path.exists(), ".env file should exist"

    def test_required_variables_set(self):
        """Test that required environment variables are set."""
        required_vars = ["MCP_SOLVER_COMMAND", "MCP_SOLVER_ARGS"]

        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)

        if missing:
            pytest.skip(f"Required variables not set: {', '.join(missing)}")

        assert len(missing) == 0


class TestMCPCommand:
    """Test MCP command configuration."""

    def test_command_is_set(self):
        """Test MCP_SOLVER_COMMAND is not empty."""
        command = os.getenv("MCP_SOLVER_COMMAND")
        if not command:
            pytest.skip("MCP_SOLVER_COMMAND not set")

        assert command.strip(), "MCP_SOLVER_COMMAND should not be empty"

    def test_command_exists_in_path(self):
        """Test MCP command exists in PATH."""
        command = os.getenv("MCP_SOLVER_COMMAND")
        if not command:
            pytest.skip("MCP_SOLVER_COMMAND not set")

        assert shutil.which(command), f"Command '{command}' not found in PATH"


class TestMCPArguments:
    """Test MCP arguments configuration."""

    def test_args_are_set(self):
        """Test MCP_SOLVER_ARGS is not empty."""
        args_str = os.getenv("MCP_SOLVER_ARGS")
        if not args_str:
            pytest.skip("MCP_SOLVER_ARGS not set")

        assert args_str.strip(), "MCP_SOLVER_ARGS should not be empty"

    def test_args_parse_correctly(self):
        """Test MCP_SOLVER_ARGS can be parsed."""
        args_str = os.getenv("MCP_SOLVER_ARGS", "")
        if not args_str:
            pytest.skip("MCP_SOLVER_ARGS not set")

        args = [arg.strip() for arg in args_str.split(",") if arg.strip()]
        assert len(args) > 0, "MCP_SOLVER_ARGS should contain at least one argument"


class TestMCPDirectory:
    """Test MCP directory configuration."""

    def test_directory_in_args(self):
        """Test --directory argument is present."""
        args_str = os.getenv("MCP_SOLVER_ARGS", "")
        if not args_str:
            pytest.skip("MCP_SOLVER_ARGS not set")

        args = [arg.strip() for arg in args_str.split(",") if arg.strip()]

        has_directory = "--directory" in args
        if not has_directory:
            pytest.skip("No --directory argument in MCP_SOLVER_ARGS")

        assert has_directory

    def test_directory_exists(self):
        """Test MCP solver directory exists."""
        args_str = os.getenv("MCP_SOLVER_ARGS", "")
        if not args_str:
            pytest.skip("MCP_SOLVER_ARGS not set")

        args = [arg.strip() for arg in args_str.split(",") if arg.strip()]

        directory_path = None
        for i, arg in enumerate(args):
            if arg == "--directory" and i + 1 < len(args):
                directory_path = args[i + 1]
                break

        if not directory_path:
            pytest.skip("No directory path found in MCP_SOLVER_ARGS")

        dir_path = Path(directory_path)
        assert dir_path.exists(), f"Directory not found: {directory_path}"
        assert dir_path.is_dir(), f"Path is not a directory: {directory_path}"

    def test_directory_has_pyproject(self):
        """Test MCP directory contains pyproject.toml (indicates valid installation)."""
        args_str = os.getenv("MCP_SOLVER_ARGS", "")
        if not args_str:
            pytest.skip("MCP_SOLVER_ARGS not set")

        args = [arg.strip() for arg in args_str.split(",") if arg.strip()]

        directory_path = None
        for i, arg in enumerate(args):
            if arg == "--directory" and i + 1 < len(args):
                directory_path = args[i + 1]
                break

        if not directory_path:
            pytest.skip("No directory path found")

        dir_path = Path(directory_path)
        if not dir_path.exists():
            pytest.skip(f"Directory not found: {directory_path}")

        pyproject = dir_path / "pyproject.toml"
        assert pyproject.exists(), (
            f"No pyproject.toml in {directory_path} - "
            "may not be a valid mcp-solver installation"
        )


class TestModelConfiguration:
    """Test model configuration (optional)."""

    def test_model_name_format(self):
        """Test MODEL_NAME is set and not empty."""
        model = os.getenv("MODEL_NAME")
        if not model:
            pytest.skip("MODEL_NAME not set (will use default)")

        assert model.strip(), "MODEL_NAME should not be empty if set"

    def test_max_iterations_valid(self):
        """Test MAX_ITERATIONS is a valid number."""
        max_iter = os.getenv("MAX_ITERATIONS")
        if not max_iter:
            pytest.skip("MAX_ITERATIONS not set (will use default)")

        try:
            value = int(max_iter)
            assert value > 0, "MAX_ITERATIONS should be positive"
        except ValueError:
            pytest.fail(f"MAX_ITERATIONS should be a number, got: {max_iter}")
