"""Setup script for AIEO CLI."""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="aieo",
    version="0.1.0",
    author="AIEO Team",
    description="AI Engine Optimization CLI tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "click>=8.0.0",
        "httpx>=0.26.0",
    ],
    entry_points={
        "console_scripts": [
            "aieo=aieo.cli:cli",
        ],
    },
)


