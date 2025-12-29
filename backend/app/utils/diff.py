"""Diff utilities for showing content changes."""

from typing import List, Dict
import difflib


def generate_diff(original: str, optimized: str) -> List[Dict]:
    """
    Generate diff between original and optimized content.

    Returns:
        List of change dictionaries with location and text
    """
    changes = []

    # Use difflib to find differences
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        optimized.splitlines(keepends=True),
        lineterm="",
    )

    current_pos = 0
    for line in diff:
        if line.startswith("@@"):
            # Parse hunk header
            continue
        elif line.startswith("+") and not line.startswith("+++"):
            # Added line
            changes.append(
                {
                    "type": "add",
                    "line": current_pos,
                    "text": line[1:],
                }
            )
            current_pos += 1
        elif line.startswith("-") and not line.startswith("---"):
            # Removed line
            changes.append(
                {
                    "type": "remove",
                    "line": current_pos,
                    "text": line[1:],
                }
            )
        elif line.startswith(" "):
            # Unchanged line
            current_pos += 1

    return changes


def calculate_text_diff(original: str, optimized: str) -> Dict:
    """
    Calculate text-level diff statistics.

    Returns:
        Dictionary with diff statistics
    """
    original_words = original.split()
    optimized_words = optimized.split()

    # Calculate word-level differences
    matcher = difflib.SequenceMatcher(None, original_words, optimized_words)

    return {
        "similarity": matcher.ratio(),
        "added_words": len(optimized_words) - len(original_words),
        "changed_blocks": len(list(matcher.get_opcodes())),
    }
