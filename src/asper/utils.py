import json
import logging
from pathlib import Path

def read_text_file(prompt_path: Path) -> str:
    if not prompt_path.exists():
        raise FileNotFoundError(f"File not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")

def export_solution(problem_path: Path, results: dict, export_path: Path = Path("results")) -> dict[str, Path]:
    base_path = export_path / problem_path
    base_path.parent.mkdir(parents=True, exist_ok=True)

    exported_files = {}

    json_path = base_path.with_suffix(".json")
    with open(json_path, "w", encoding='utf-8') as json_file:
        json.dump(results, json_file, indent=4)
    exported_files["json"] = json_path

    asp_code = results.get("asp_code")
    if asp_code:
        lp_path = base_path.with_suffix(".lp")
        with open(lp_path, "w", encoding='utf-8') as lp_file:
            lp_file.write(asp_code)
        exported_files["lp"] = lp_path

    return exported_files

def load_solution(solution_path: Path) -> dict:
    try:
        with solution_path.open('r', encoding='utf-8') as solution:
            return json.load(solution)
    except FileNotFoundError as e:
        print("File not found.")

def setup_logger(problem_path: Path, logging_level: str, export_path: Path = Path("results")) -> logging.Logger:
    # Configure logging once for the CLI
    export_file_path = (export_path / problem_path).with_suffix(".log")
    Path(export_file_path.parent).mkdir(parents=True, exist_ok=True)
    logging_format = "%(asctime)s %(levelname)s %(name)s - %(message)s"
    
    logger = logging.getLogger("log")
    logger.setLevel(logging_level)
    
    formatter = logging.Formatter(logging_format)
    file_handler = logging.FileHandler(export_file_path, mode='w')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging_level)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

def get_logger() -> logging.Logger:
    return logging.getLogger("log")

def reset_logger():
    logger = logging.getLogger("log")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    logger.propagate = False