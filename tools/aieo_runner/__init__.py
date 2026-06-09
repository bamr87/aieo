"""Headless markdown audit/optimize runner for CI and local use."""

from .discover import discover_files, discover_git_diff_paths

__all__ = ["discover_files", "discover_git_diff_paths"]
