# Contributing to AIEO

Thank you for your interest in contributing to AIEO! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- A clear, descriptive title
- Steps to reproduce the bug
- Expected behavior vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or error messages

### Suggesting Features

Feature suggestions are welcome! Please open an issue with:
- A clear description of the feature
- Use cases and examples
- Potential implementation approach (if you have ideas)

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
   - Follow the coding standards (see below)
   - Add tests for new features
   - Update documentation as needed
4. **Commit your changes**:
   ```bash
   git commit -m "feat: add your feature description"
   ```
   Use [Conventional Commits](https://www.conventionalcommits.org/) format.
5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Open a Pull Request** with a clear description

## Development Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- Docker and Docker Compose
- Git

### Initial Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/aieo.git
   cd aieo
   ```

2. **Run installation script**:
   ```bash
   ./scripts/install.sh  # Linux/macOS
   # OR
   python scripts/install.py  # Windows
   ```

3. **Set up environment variables**:
   ```bash
   cp env.example .env
   # Edit .env and add your API keys
   ```

4. **Start development servers**:
   ```bash
   # Backend
   cd backend
   source venv/bin/activate
   uvicorn app.main:app --reload

   # Frontend (in another terminal)
   cd frontend
   npm run dev
   ```

## Coding Standards

### Python (Backend)

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints
- Maximum line length: 100 characters
- Use `black` for formatting:
  ```bash
  black backend/
  ```
- Use `ruff` for linting:
  ```bash
  ruff check backend/
  ```

### TypeScript/React (Frontend)

- Follow ESLint rules
- Use TypeScript for type safety
- Use functional components with hooks
- Format with Prettier:
  ```bash
  npm run format
  ```

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

Examples:
```
feat: add comparison table detection
fix: resolve scoring engine edge case
docs: update API documentation
```

## Testing

### Backend Tests

```bash
cd backend
source venv/bin/activate
pytest
```

### Frontend Tests

```bash
cd frontend
npm test
```

### Integration Tests

```bash
python tools/testing/comprehensive_test.py
```

## Documentation

- Update relevant documentation when adding features
- Add docstrings to new functions/classes
- Update API docs if changing endpoints
- Update README if changing setup/usage

## Project Structure

```
aieo/
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── api/      # API endpoints
│   │   ├── core/     # Core utilities
│   │   ├── models/   # Database models
│   │   └── services/ # Business logic
│   └── tests/       # Backend tests
├── frontend/         # React frontend
├── cli/              # CLI tool
├── docs/             # Documentation
├── scripts/          # Setup scripts
└── tools/            # Testing tools
```

## Review Process

1. All PRs require at least one review
2. CI checks must pass
3. Code coverage should not decrease
4. Documentation must be updated

## Questions?

- Open an issue for questions
- Check existing documentation in `docs/`
- Review [ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design

Thank you for contributing! 🎉

