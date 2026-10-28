"""Repository context extraction and ranking via AST and keyword matching."""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any


def rank_repo_files(repo_dir: Path, terms: list[str]) -> list[Path]:
    """Rank Python files in repo_dir by occurrence of terms from issue and failure."""
    if not repo_dir.is_dir():
        return []

    scores: dict[Path, int] = {}
    valid_terms = [t.lower() for t in terms if len(t) > 2]

    for py_file in repo_dir.rglob("*.py"):
        if ".git" in py_file.parts or "__pycache__" in py_file.parts or "hidden_tests" in py_file.parts:
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore").lower()
            score = 0
            for term in valid_terms:
                score += content.count(term)
            if score > 0:
                scores[py_file] = score
        except Exception:
            continue

    # Return sorted by score descending
    return sorted(scores.keys(), key=lambda p: scores[p], reverse=True)


def extract_relevant_ast_snippets(file_path: Path, terms: list[str], max_chars: int = 3000) -> str:
    """Extract matching classes and functions via AST plus surrounding lines."""
    try:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(file_path))
    except Exception:
        # Fallback to truncated raw file
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()[:60]
        return "\n".join(lines)[:max_chars]

    lines = source.splitlines()
    matching_nodes: list[tuple[int, int]] = []
    lower_terms = [t.lower() for t in terms if len(t) > 2]

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = node.name.lower()
            matches = any(t in name for t in lower_terms)
            if not matches and hasattr(node, "body"):
                node_text = ast.get_source_segment(source, node) or ""
                matches = any(t in node_text.lower() for t in lower_terms)
            if matches and hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                start = max(1, node.lineno - 2)
                end = min(len(lines), (node.end_lineno or node.lineno) + 2)
                matching_nodes.append((start, end))

    if not matching_nodes:
        # If no AST node matches specifically, grab first 50 lines
        return "\n".join(lines[:50])[:max_chars]

    # Merge overlapping ranges
    matching_nodes.sort()
    merged: list[tuple[int, int]] = []
    for start, end in matching_nodes:
        if merged and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    snippets = []
    total_len = 0
    for start, end in merged:
        chunk = f"# {file_path.name} lines {start}-{end}:\n" + "\n".join(lines[start - 1 : end])
        if total_len + len(chunk) > max_chars:
            snippets.append(chunk[: max_chars - total_len])
            break
        snippets.append(chunk)
        total_len += len(chunk)

    return "\n\n".join(snippets)


def build_context(repo_dir: Path, issue_text: str, failure_summary: str, max_tokens: int = 8000) -> str:
    """Build compact repo context hard-capped at max_tokens."""
    max_chars = max_tokens * 4

    # Extract search terms from issue and failure
    raw_terms = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", f"{issue_text} {failure_summary}")
    terms = list(dict.fromkeys(raw_terms))[:20]

    ranked_files = rank_repo_files(repo_dir, terms)
    if not ranked_files:
        # Grab any non-test py files in repo root
        ranked_files = [f for f in repo_dir.glob("*.py") if not f.name.startswith("test_")]

    snippets = []
    current_chars = 0
    per_file_cap = min(2500, max_chars // max(1, len(ranked_files[:4])))

    for path in ranked_files[:4]:
        snippet = extract_relevant_ast_snippets(path, terms, max_chars=per_file_cap)
        formatted = f"--- {path.relative_to(repo_dir)} ---\n{snippet}"
        if current_chars + len(formatted) > max_chars:
            snippets.append(formatted[: max_chars - current_chars])
            break
        snippets.append(formatted)
        current_chars += len(formatted)

    return "\n\n".join(snippets)
