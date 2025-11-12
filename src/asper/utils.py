"""Utility functions for file I/O, solution export, and logging setup.

Provides helpers for reading problem files, exporting ASP solutions to JSON/LP,
loading results, and configuring file+console logging for ASP runs.
"""
import re
import json
import logging
from pathlib import Path


def read_text_file(prompt_path: Path) -> str:
    """Read text file content from the given path.

    Args:
        prompt_path: Path to the text file

    Returns:
        File content as string

    Raises:
        FileNotFoundError: If file does not exist
    """
    if not prompt_path.exists():
        raise FileNotFoundError(f"File not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def export_solution(
    problem_path: Path, results: dict, export_path: Path = Path("results")
) -> dict[str, Path]:
    """Export solution results to JSON and optionally LP files.

    Args:
        problem_path: Original problem file path (used for naming)
        results: Solution dictionary containing asp_code and metadata
        export_path: Base directory for exports (default: results/)

    Returns:
        Dictionary mapping file types ('json', 'lp') to exported Path objects
    """
    base_path = export_path / problem_path
    base_path.parent.mkdir(parents=True, exist_ok=True)

    exported_files = {}

    json_path = base_path.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(results, json_file, indent=4)
    exported_files["json"] = json_path

    asp_code = results.get("asp_code")
    if asp_code:
        lp_path = base_path.with_suffix(".lp")
        with open(lp_path, "w", encoding="utf-8") as lp_file:
            lp_file.write(asp_code)
        exported_files["lp"] = lp_path

    return exported_files


def load_solution(solution_path: Path) -> dict | None:
    """Load a previously exported solution from JSON.

    Args:
        solution_path: Path to the JSON solution file

    Returns:
        Solution dictionary, or None if file not found
    """
    try:
        with solution_path.open("r", encoding="utf-8") as solution:
            return json.load(solution)
    except FileNotFoundError:
        print("File not found.")


def setup_logger(
    problem_path: Path, logging_level: str, export_path: Path = Path("results")
) -> logging.Logger:
    """Configure logger with file and console handlers for an ASP run.

    Creates a log file alongside the solution output and attaches both
    file (detailed) and console (INFO+) handlers.

    Args:
        problem_path: Problem file path (used for log file naming)
        logging_level: Log level string (e.g., 'DEBUG', 'INFO')
        export_path: Base directory for log files (default: results/)

    Returns:
        Configured logger instance named 'log'
    """
    export_file_path = (export_path / problem_path).with_suffix(".log")
    Path(export_file_path.parent).mkdir(parents=True, exist_ok=True)
    logging_format = "%(asctime)s %(levelname)s %(name)s - %(message)s"

    logger = logging.getLogger("log")
    logger.setLevel(logging_level)

    formatter = logging.Formatter(logging_format)
    file_handler = logging.FileHandler(export_file_path, mode="w")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging_level)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_logger() -> logging.Logger:
    """Get the current ASP system logger.

    Returns:
        Logger instance named 'log'
    """
    return logging.getLogger("log")


def reset_logger():
    """Remove and close all handlers from the ASP system logger.

    Used to clean up logging configuration between batch runs.
    """
    logger = logging.getLogger("log")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    logger.propagate = False


def extract_predicates(text):
    """Extract predicate names and arities from ASP code."""
    pred_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^()]*)\)')
    
    preds = []
    for name, args in pred_pattern.findall(text):
        arity = 0 if args.strip() == "" else len([a for a in args.split(',') if a.strip()])
        preds.append(f"{name}/{arity}")
    return preds

def preprocess_multiline_rules(lines):
    """
    Join multi-line ASP rules: lines ending with ',' or where next line starts with a space.
    Also merge lines until a terminating '.'.
    """
    merged = []
    current = ""

    for line in lines:
        stripped = line.strip()

        # Preserve comments and directives as is
        if stripped.startswith('%') or stripped.startswith('#'):
            if current:
                merged.append(current)
                current = ""
            merged.append(line)
            continue

        # Accumulate rule lines until a final '.'
        if stripped:
            current += " " + stripped
            if stripped.endswith('.'):
                merged.append(current.strip())
                current = ""
        else:
            # empty line, flush any accumulated rule
            if current:
                merged.append(current.strip())
                current = ""

    if current:  # flush last rule if not terminated
        merged.append(current.strip())

    return merged

def analyze_asp_code(asp_code: str) -> tuple[str, set]:
    """Find unused rules and comment them out."""
    raw_lines = asp_code.splitlines()
    lines = preprocess_multiline_rules(raw_lines)

    rules = []
    shows = set()
    heads = set()
    bodies = set()
    facts = set()

    # Step 1: Collect #show and facts predicates
    for line in lines:
        show_match = re.findall(r"#show\s+([a-zA-Z_][a-zA-Z0-9_]*)/(\d+)", line)
        for name, arity in show_match:
            shows.add(f"{name}/{arity}")
        
        stripped = line.strip()
        if ':-' not in line and '.' in line and not stripped.startswith('%') and not stripped.startswith('#'):
            for p in extract_predicates(line):
                facts.add(p)

    # Step 2: Parse rules
    for i, line in enumerate(lines):
        if line.strip().startswith('%') or line.strip().startswith('#') or not line.strip():
            continue  # skip comments, #directives, and empty lines
        
        # Separate head and body
        if ':-' in line:
            head_part, body_part = line.split(':-', 1)
        else:
            head_part, body_part = line, ''

        # Find predicates in head and body
        head_preds = extract_predicates(head_part)
        body_preds = extract_predicates(body_part)

        for h in head_preds:
            heads.add(h)
        for b in body_preds:
            bodies.add(b)

        rules.append((i, head_preds, body_preds))

    # Step 3: Determine unused heads
    unused_heads = {h for h in heads if h not in bodies and h not in shows and h not in facts}

    # Step 4: Comment out rules whose *all* heads are unused
    output_lines = []
    for i, line in enumerate(lines):
        rule = next((r for r in rules if r[0] == i), None)
        if rule:
            head_preds, _ = rule[1], rule[2]
            if all(h in unused_heads for h in head_preds):
                line = "% " + line  # comment it
        output_lines.append(line)

    return "\n".join(output_lines), unused_heads