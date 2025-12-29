# AIEO - AI Engine Optimization

[![CI](https://github.com/bamr87/aieo/workflows/CI/badge.svg)](https://github.com/bamr87/aieo/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)

**AIEO** (AI Engine Optimization) is the new SEO. Optimize your content to maximize citations from AI engines like Grok, ChatGPT, Claude, Gemini, and Perplexity.

## 🎯 What is AIEO?

AIEO helps content creators optimize their content to be preferentially cited by AI engines. Instead of optimizing for search engines, optimize for the AI engines that are becoming the primary discovery layer.

### Key Features

- ✅ **Content Auditing** - Get an AIEO score (0-100) with detailed gap analysis
- ✅ **Pattern Detection** - Identify 10 proven AIEO patterns in your content
- ✅ **Optimization Suggestions** - AI-powered recommendations to improve citations
- ✅ **Benchmark Comparison** - See how your content ranks against others
- ✅ **Web UI** - Beautiful interface for content analysis
- ✅ **CLI Tool** - Command-line interface for automation
- ✅ **REST API** - Integrate AIEO into your workflow

## 🚀 Quick Start

## Project Structure

```
aieo/
├── backend/          # FastAPI backend
├── frontend/         # React frontend
├── cli/             # Python CLI tool
└── docker-compose.yml
```

## Quick Start

### Automated Installation (Recommended)

**Linux/macOS:**
```bash
./scripts/install.sh
```

**Windows or Cross-platform:**
```bash
python scripts/install.py
```

The installation script will automatically:
- Check prerequisites
- Set up backend, frontend, and CLI
- Configure environment
- Start Docker services
- Run database migrations

See [INSTALL.md](INSTALL.md) for detailed installation instructions.

### Manual Installation

If you prefer manual setup, see [INSTALL.md](INSTALL.md) for step-by-step instructions.

### Prerequisites

- Docker and Docker Compose
- Python 3.9+ (for backend and CLI)
- Node.js 18+ (for frontend)

### Quick Setup

1. **Run installation script:**
   ```bash
   ./scripts/install.sh  # Linux/macOS
   # OR
   python scripts/install.py  # Windows/Cross-platform
   ```

2. **Edit `.env` file and add your API keys:**
   ```bash
   # Required:
   OPENAI_API_KEY=your-openai-api-key
   # Optional:
   ANTHROPIC_API_KEY=your-anthropic-api-key
   ```

3. **Start development servers:**
   ```bash
   # Backend (from backend/)
   cd backend
   source venv/bin/activate
   uvicorn app.main:app --reload

   # Frontend (from frontend/) - in a new terminal
   cd frontend
   npm run dev
   ```

4. **Access the application:**
   - Web UI: http://localhost:5173
   - API Docs: http://localhost:8000/docs

## Verification

After installation, verify everything is set up correctly:

```bash
./scripts/verify.sh  # Linux/macOS
# OR
python scripts/verify.py  # Windows/Cross-platform
```

## Usage

### CLI

```bash
# Make sure backend virtual environment is activated
source backend/venv/bin/activate  # Linux/macOS
# OR
backend\venv\Scripts\activate  # Windows

# Audit content
aieo audit https://example.com/article
aieo audit --file article.md

# Optimize content
aieo optimize article.md --output optimized.md

# View dashboard
aieo dashboard
```

### Web UI

Visit http://localhost:5173 to use the web interface.

### API

API documentation available at http://localhost:8000/docs

## Development

```bash
# Run tests
make test

# Format code
make format

# Lint code
make lint

# Clean generated files
make clean
```

## 📚 Documentation

- [Installation Guide](INSTALL.md) - Detailed setup instructions
- [API Documentation](docs/API.md) - API reference
- [CLI Documentation](docs/CLI.md) - CLI usage guide
- [Patterns Guide](docs/PATTERNS.md) - AIEO patterns explained
- [Architecture](docs/ARCHITECTURE.md) - System design
- [Development Guide](docs/DEVELOPMENT.md) - Contributing guide
- [PRD](PRD-aieo.md) - Product requirements document

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security Policy](SECURITY.md)
- [Development Guide](docs/DEVELOPMENT.md)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Frontend powered by [React](https://react.dev/) and [TypeScript](https://www.typescriptlang.org/)
- Inspired by the need to optimize for AI-first discovery

## 📞 Support

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/bamr87/aieo/issues)
- 💬 [Discussions](https://github.com/bamr87/aieo/discussions)

---

**Made with ❤️ for content creators who want to be cited by AI engines**

