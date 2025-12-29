# Development Guide

This guide covers development workflows, coding standards, and best practices for AIEO.

## Development Environment Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- Docker and Docker Compose
- Git

### Initial Setup

1. **Clone and install:**
   ```bash
   git clone https://github.com/your-username/aieo.git
   cd aieo
   ./scripts/install.sh
   ```

2. **Configure environment:**
   ```bash
   cp env.example .env
   # Edit .env with your API keys
   ```

3. **Start services:**
   ```bash
   docker-compose up -d
   ```

## Development Workflow

### Backend Development

1. **Activate virtual environment:**
   ```bash
   cd backend
   source venv/bin/activate
   ```

2. **Run development server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Run tests:**
   ```bash
   pytest
   ```

4. **Format code:**
   ```bash
   black backend/
   ```

5. **Lint code:**
   ```bash
   ruff check backend/
   ```

### Frontend Development

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Run development server:**
   ```bash
   npm run dev
   ```

3. **Build for production:**
   ```bash
   npm run build
   ```

4. **Run tests:**
   ```bash
   npm test
   ```

### CLI Development

1. **Install in development mode:**
   ```bash
   cd cli
   pip install -e .
   ```

2. **Test commands:**
   ```bash
   aieo audit --help
   ```

## Code Standards

### Python

- **Style:** PEP 8
- **Type hints:** Required for public APIs
- **Line length:** 100 characters
- **Formatter:** Black
- **Linter:** Ruff
- **Docstrings:** Google style

**Example:**
```python
def score_content(content: str, format: str = "markdown") -> Dict[str, Any]:
    """
    Score content against AIEO patterns.
    
    Args:
        content: Content to score
        format: Content format ('markdown' or 'html')
    
    Returns:
        Dictionary with score, grade, and gaps
    """
    ...
```

### TypeScript/React

- **Style:** ESLint + Prettier
- **Type safety:** Strict TypeScript
- **Components:** Functional with hooks
- **Naming:** PascalCase for components, camelCase for functions

**Example:**
```typescript
interface AuditResult {
  score: number;
  grade: string;
  gaps: Gap[];
}

export function AuditPage() {
  const [result, setResult] = useState<AuditResult | null>(null);
  ...
}
```

## Testing

### Backend Tests

```bash
cd backend
pytest                    # Run all tests
pytest tests/test_scoring_engine.py  # Run specific test
pytest -v                # Verbose output
pytest --cov=app         # With coverage
```

### Frontend Tests

```bash
cd frontend
npm test                 # Run tests
npm test -- --watch      # Watch mode
npm test -- --coverage   # With coverage
```

### Integration Tests

```bash
python tools/testing/comprehensive_test.py
```

## Database Migrations

### Create Migration

```bash
cd backend
alembic revision --autogenerate -m "description"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback

```bash
alembic downgrade -1
```

## API Development

### Adding New Endpoint

1. **Create endpoint in `app/api/v1/`:**
   ```python
   @router.post("/aieo/new-endpoint")
   async def new_endpoint(
       request: NewRequest,
       api_key: str = Depends(verify_api_key),
   ):
       ...
   ```

2. **Add request/response models:**
   ```python
   class NewRequest(BaseModel):
       field: str
   ```

3. **Update API documentation:**
   - Endpoints auto-document at `/docs`
   - Add examples in docstrings

## Debugging

### Backend Debugging

```bash
# Run with debug logging
uvicorn app.main:app --reload --log-level debug

# Use Python debugger
import pdb; pdb.set_trace()
```

### Frontend Debugging

- Use React DevTools
- Browser DevTools
- Console logging

### Database Debugging

```bash
# Connect to database
docker-compose exec postgres psql -U aieo -d aieo

# View logs
docker-compose logs postgres
```

## Git Workflow

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `refactor/` - Refactoring
- `test/` - Tests

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add comparison table detection
fix: resolve scoring edge case
docs: update API documentation
refactor: improve content parser
test: add integration tests
```

### Pull Request Process

1. Create feature branch
2. Make changes
3. Write/update tests
4. Update documentation
5. Ensure tests pass
6. Create PR with description
7. Address review comments
8. Merge after approval

## Performance Optimization

### Backend

- Use async/await for I/O operations
- Cache expensive operations
- Optimize database queries
- Use connection pooling

### Frontend

- Code splitting
- Lazy loading
- Memoization
- Optimize re-renders

## Common Tasks

### Add New Pattern

1. Update `scoring_engine.py`
2. Add detection logic
3. Update tests
4. Update documentation

### Add New Service

1. Create service file in `app/services/`
2. Add tests
3. Integrate with API
4. Update documentation

### Update Dependencies

```bash
# Backend
cd backend
pip list --outdated
pip install --upgrade package

# Frontend
cd frontend
npm outdated
npm update package
```

## Troubleshooting

### Common Issues

**Backend won't start:**
- Check database connection
- Verify environment variables
- Check port availability

**Frontend build fails:**
- Clear node_modules and reinstall
- Check Node.js version
- Verify dependencies

**Tests fail:**
- Check test database setup
- Verify environment variables
- Check for port conflicts

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

## Getting Help

- Check existing issues
- Review documentation
- Ask in discussions
- Open an issue with details

