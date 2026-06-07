"""Ensure no concrete provider imports leak outside adapters/*."""
import ast
from pathlib import Path


EXCLUDED_DIRS = {'adapters', 'tests', '__pycache__', 'venv', '.venv', 'node_modules'}
FORBIDDEN_IMPORTS = [
    'import anthropic',
    'import google.genai',
    'import fal_client',
    'import openai',
]


def find_python_files(root: Path):
    for path in root.rglob('*.py'):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        yield path


def check_file(path: Path) -> list[str]:
    errors = []
    text = path.read_text(encoding='utf-8')
    for forbidden in FORBIDDEN_IMPORTS:
        if forbidden in text:
            errors.append(f"{path}: found '{forbidden}'")
    return errors


def test_no_leaky_imports():
    backend = Path(__file__).parent.parent.parent / 'backend'
    all_errors = []
    for path in find_python_files(backend):
        all_errors.extend(check_file(path))
    assert not all_errors, "Leaky imports found: " + " | ".join(all_errors)
