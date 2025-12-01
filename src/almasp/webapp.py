"""
Streamlit Web Application for Agentic ASP Solver
Provides an interactive UI for solving ASP problems with live logging.
"""
import os
import time
import threading
import asyncio
import logging
import tempfile
import sys
import subprocess
from pathlib import Path
from io import StringIO

import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

from almasp.config import ASPSystemConfig
from almasp.runner import ASPRunner


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "run_thread": None,
        "result": None,
        "error": None,
        "running": False,
        "log_stream": None,
        "stop_requested": False,
        "execution_completed": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================================
# CONFIGURATION BUILDERS
# ============================================================================

def build_config(api_key: str, base_url: str, model_name: str, provider: str,
                reasoning: str, temperature: float, max_iterations: int,
                solver_prompt_text: str, validator_prompt_text: str) -> ASPSystemConfig:
    """Build ASP system configuration from UI parameters."""
    # Set environment variables
    os.environ["PROVIDER_API_KEY"] = api_key
    os.environ["PROVIDER_BASE_URL"] = base_url
    os.environ["MODEL_NAME"] = model_name
    
    # Create temporary prompt files if provided
    solver_prompt_file = _create_temp_prompt_file(solver_prompt_text, "solver")
    validator_prompt_file = _create_temp_prompt_file(validator_prompt_text, "validator")
    
    return ASPSystemConfig.from_env(
        model_name=model_name,
        max_iterations=max_iterations,
        solver_prompt_file=solver_prompt_file,
        validator_prompt_file=validator_prompt_file,
        provider=provider,
        reasoning=reasoning,
        temperature=temperature,
    )


def _create_temp_prompt_file(prompt_text: str, prefix: str) -> str | None:
    """Create a temporary file for custom prompt text."""
    if not prompt_text.strip():
        return None
    
    tmp = tempfile.NamedTemporaryFile(
        suffix=".txt",
        prefix=f"{prefix}_prompt_",
        delete=False,
        mode="w",
        encoding="utf-8"
    )
    tmp.write(prompt_text)
    tmp.flush()
    tmp.close()
    return tmp.name


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging(log_stream: StringIO, log_level: str) -> logging.Logger:
    """Configure logging to capture all output to a string stream."""
    # Main webapp logger
    logger = logging.getLogger("almasp_webapp")
    logger.setLevel(getattr(logging, log_level))
    logger.handlers.clear()
    logger.propagate = False
    
    # Create handler
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(getattr(logging, log_level))
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Capture all "log" module loggers (including submodules)
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        if logger_name.startswith("log"):
            sub_logger = logging.getLogger(logger_name)
            sub_logger.setLevel(getattr(logging, log_level))
            sub_logger.handlers.clear()
            sub_logger.propagate = False
            sub_logger.addHandler(handler)
    
    return logger


# ============================================================================
# BACKGROUND EXECUTION
# ============================================================================

def background_run(problem: str, log_level: str, config: ASPSystemConfig):
    """
    Background thread target: run the ASP solver.
    Updates session state with results and logs.
    """
    tmp_file = None
    task = None
    
    try:
        # Setup logging
        log_stream = StringIO()
        st.session_state.log_stream = log_stream
        logger = setup_logging(log_stream, log_level)
        
        logger.info("Starting ASP solver...")

        # Check for early stop
        if st.session_state.stop_requested:
            logger.warning("Execution stopped by user before starting")
            return

        # Create temporary problem file
        tmp_file = _create_problem_file(problem)
        tmp_path = Path(tmp_file.name)

        # Initialize runner
        runner = ASPRunner(config, logger)
        logger.info("Running solver...")
        
        # Execute with cancellation support
        task = _run_with_cancellation(runner, tmp_path, logger)
        
        if task and not st.session_state.stop_requested:
            st.session_state.result = task
            logger.info("Execution completed")
            st.session_state.execution_completed = True

    except asyncio.CancelledError:
        logger.warning("Execution cancelled by user")
        st.session_state.error = "Execution stopped by user"
        st.session_state.execution_completed = True
        
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
        st.session_state.error = error_msg
        st.session_state.execution_completed = True
        try:
            if 'logger' in locals():
                logger.error(f"Run failed: {error_msg}")
        except:
            pass
            
    finally:
        # Cleanup
        _cleanup_temp_file(tmp_file)
        st.session_state.running = False
        st.session_state.run_thread = None
        st.session_state.stop_requested = False


def _create_problem_file(problem: str):
    """Create a temporary file for the problem description."""
    tmp_file = tempfile.NamedTemporaryFile(
        suffix=".md",
        prefix="asp_problem_",
        delete=False,
        mode="w",
        encoding="utf-8"
    )
    tmp_file.write(problem)
    tmp_file.flush()
    tmp_file.close()
    return tmp_file


def _run_with_cancellation(runner: ASPRunner, problem_path: Path, logger: logging.Logger):
    """Run the solver with support for cancellation via stop button."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        task = loop.create_task(runner.solve(problem_path))
        
        # Poll for completion or stop request
        while not task.done():
            if st.session_state.stop_requested:
                logger.warning("Stop requested - cancelling task...")
                task.cancel()
                try:
                    loop.run_until_complete(task)
                except asyncio.CancelledError:
                    logger.info("Task cancelled successfully")
                    st.session_state.error = "Execution stopped by user"
                return None
            
            loop.run_until_complete(asyncio.sleep(0.1))
        
        return task.result()
        
    finally:
        loop.close()


def _cleanup_temp_file(tmp_file):
    """Clean up temporary file."""
    if tmp_file:
        try:
            os.unlink(tmp_file.name)
        except:
            pass


# ============================================================================
# UI ACTIONS
# ============================================================================

def start_run(problem_text: str, log_level: str, config: ASPSystemConfig):
    """Start the solver execution in a background thread."""
    # Reset state
    st.session_state.result = None
    st.session_state.error = None
    st.session_state.running = True
    st.session_state.log_stream = None
    st.session_state.stop_requested = False
    st.session_state.execution_completed = False

    # Create and start thread
    t = threading.Thread(
        target=background_run,
        args=(problem_text, log_level, config),
        daemon=True
    )
    
    # Add script context to suppress warnings
    ctx = get_script_run_ctx()
    if ctx:
        add_script_run_ctx(t, ctx)
    
    st.session_state.run_thread = t
    t.start()


def stop_run():
    """Request to stop the current execution."""
    st.session_state.stop_requested = True
    st.session_state.running = False
    st.session_state.execution_completed = True
    if st.session_state.log_stream:
        st.session_state.log_stream.write("\n\n[STOP REQUESTED BY USER]\n")


def get_log_content() -> str:
    """Get current log content from the stream."""
    if st.session_state.log_stream:
        return st.session_state.log_stream.getvalue()
    return "Initializing..."


# ============================================================================
# UI RENDERING
# ============================================================================

def render_sidebar():
    """Render the configuration sidebar."""
    with st.sidebar:
        st.header("Configuration")

        # API Configuration
        api_key = st.text_input(
            "PROVIDER_API_KEY",
            value=os.getenv("PROVIDER_API_KEY", ""),
            type="password"
        )
        
        provider = st.selectbox("Provider", options=["ollama", "openrouter"], index=0)
        
        base_url = "http://localhost:11434/v1" if provider == "ollama" else "https://openrouter.ai/api/v1"
        st.text_input("Base URL", value=base_url, disabled=True, help="Automatically set based on provider")
        
        # Model Configuration
        model_name = st.text_input("MODEL_NAME", value=os.getenv("MODEL_NAME", "gpt-oss:120b"))
        reasoning = st.selectbox("Reasoning mode", options=["false", "true", "low", "medium", "high"], index=0)
        temperature = st.slider("Temperature", 0.0, 1.0, 0.0, 0.05)
        max_iterations = st.number_input("Max Iterations", min_value=1, max_value=100, value=5)
        
        # Logging
        log_level = st.selectbox("Log Level", options=["INFO", "DEBUG", "WARNING", "ERROR"], index=0)
        
        st.caption("Configure parameters and click Solve below.")
    
    return api_key, provider, base_url, model_name, reasoning, temperature, max_iterations, log_level


def render_input_tabs():
    """Render input tabs for problem and prompts."""
    tab_problem, tab_solver_prompt, tab_validator_prompt = st.tabs([
        "Problem Description",
        "Solver System Prompt",
        "Validator System Prompt"
    ])

    with tab_problem:
        problem_text = st.text_area(
            "Problem Description",
            height=300,
            placeholder="Describe the problem to solve with Answer Set Programming...",
            label_visibility="collapsed",
            key="problem_text_input"
        )

    with tab_solver_prompt:
        solver_prompt_text = st.text_area(
            "Solver System Prompt",
            height=300,
            placeholder="Optional: Override the default solver system prompt...",
            label_visibility="collapsed",
            key="solver_prompt_input"
        )

    with tab_validator_prompt:
        validator_prompt_text = st.text_area(
            "Validator System Prompt",
            height=300,
            placeholder="Optional: Override the default validator system prompt...",
            label_visibility="collapsed",
            key="validator_prompt_input"
        )
    
    return problem_text, solver_prompt_text, validator_prompt_text


def render_control_buttons():
    """Render Solve and Stop buttons."""
    col1, col2, _ = st.columns([1, 1, 3])
    
    with col1:
        solve_btn = st.button(
            "Solve",
            type="primary",
            disabled=st.session_state.running,
            use_container_width=True
        )
    
    with col2:
        stop_btn = st.button(
            "Stop",
            type="secondary",
            disabled=not st.session_state.running,
            use_container_width=True
        )
    
    return solve_btn, stop_btn


def render_live_logs(tab_logs):
    """Render live updating logs during execution."""
    log_placeholder = tab_logs.empty()
    
    with st.spinner("Running agent..."):
        while st.session_state.running:
            log_text = get_log_content()
            with log_placeholder.container():
                st.code(log_text, language="text")
            
            time.sleep(0.5)
            
            # Safety check - thread died but running is still True
            if st.session_state.run_thread and not st.session_state.run_thread.is_alive():
                st.session_state.running = False
                st.session_state.execution_completed = True
                break
        
        # Final log update after loop exits
        log_text = get_log_content()
        with log_placeholder.container():
            st.code(log_text, language="text")


def render_completed_logs(tab_logs):
    """Render logs after execution completes."""
    log_text = get_log_content()
    if log_text and log_text != "Initializing...":
        with tab_logs:
            st.code(log_text, language="text")


def render_logs_column(log_container):
    """Render logs in a dedicated column that updates live."""
    with log_container:
        st.markdown("### Logs")
        log_placeholder = st.empty()
        
        if st.session_state.running:
            # Live updating logs
            while st.session_state.running:
                log_text = get_log_content()
                with log_placeholder.container():
                    st.code(log_text, language="text", height=600)
                
                time.sleep(0.5)
                
                # Safety check
                if st.session_state.run_thread and not st.session_state.run_thread.is_alive():
                    st.session_state.running = False
                    st.session_state.execution_completed = True
                    break
            
            # Final update
            log_text = get_log_content()
            with log_placeholder.container():
                st.code(log_text, language="text", height=600)
        else:
            # Show logs from completed run or idle message
            log_text = get_log_content()
            if log_text and log_text != "Initializing...":
                with log_placeholder.container():
                    st.code(log_text, language="text", height=600)
            else:
                with log_placeholder.container():
                    st.info("Logs will stream here during execution.")


def render_results(tab_code, tab_json):
    """Render execution results in appropriate tabs."""
    if st.session_state.error and not st.session_state.running:
        st.error("Run failed - check logs for details")
    
    if st.session_state.result:
        result = st.session_state.result
        
        # ASP Code tab
        with tab_code:
            asp_code = getattr(result, "asp_code", "") or ""
            if asp_code.strip():
                st.code(asp_code, language="prolog")
            else:
                st.warning("No ASP code produced.")
        
        # JSON tab
        with tab_json:
            if hasattr(result, "to_dict"):
                st.json(result.to_dict())
            else:
                st.write(result)


def render_idle_messages(tab_code, tab_json):
    """Render placeholder messages when idle."""
    with tab_code:
        st.info("Click Solve to generate ASP code.")
    with tab_json:
        st.info("Result JSON will appear after completion.")


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point."""
    # Page configuration
    st.set_page_config(page_title="Agentic ASP Solver", layout="wide")
    st.title("Agentic ASP Solver")
    
    # Initialize session state
    init_session_state()
    
    # Render sidebar configuration
    config_params = render_sidebar()
    api_key, provider, base_url, model_name, reasoning, temperature, max_iterations, log_level = config_params
    
    # Create three-column layout: main content (left) and logs (right)
    col_main, col_logs = st.columns([1, 1])
    
    with col_main:
        # Problem description and prompts
        problem_text, solver_prompt_text, validator_prompt_text = render_input_tabs()
        
        # Control buttons
        solve_btn, stop_btn = render_control_buttons()
        
        # Handle button clicks
        if solve_btn:
            if not problem_text.strip():
                st.error("Problem description is required.")
            else:
                try:
                    config = build_config(
                        api_key, base_url, model_name, provider, reasoning,
                        temperature, max_iterations, solver_prompt_text, validator_prompt_text
                    )
                    start_run(problem_text, log_level, config)
                    st.rerun()
                except Exception as e:
                    import traceback
                    st.error(f"Configuration error: {str(e)}\n\n{traceback.format_exc()}")
        
        if stop_btn:
            stop_run()
            time.sleep(0.5)
            st.rerun()
        
        # Results section
        st.markdown("---")
        st.subheader("Results")
        tab_code, tab_json = st.tabs(["ASP Code", "Result JSON"])
        
        # Render appropriate content based on state
        if st.session_state.running:
            # Show loading state in results area
            with tab_code:
                st.info("Running solver...")
            with tab_json:
                st.info("Waiting for results...")
        elif st.session_state.result or st.session_state.error:
            render_results(tab_code, tab_json)
        else:
            render_idle_messages(tab_code, tab_json)
    
    # Render logs in dedicated column
    render_logs_column(col_logs)
    
    # If execution just completed, rerun to show final results
    if st.session_state.execution_completed:
        st.session_state.execution_completed = False
        st.rerun()


# ============================================================================
# ENTRY POINT
# ============================================================================

def run_streamlit():
    """Entry point for the almasp-webapp command."""
    webapp_path = Path(__file__).resolve()
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(webapp_path)])

if __name__ == "__main__":
    main()