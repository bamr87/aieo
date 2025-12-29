# AIEO CLI Documentation

## Installation

```bash
cd cli
pip install -r requirements.txt
pip install -e .
```

## Usage

### Audit Content

```bash
# Audit a URL
aieo audit https://example.com/article

# Audit a local file
aieo audit --file article.md
aieo audit article.md

# Output as JSON
aieo audit article.md --json

# Set API key
export AIEO_API_KEY=your-api-key
aieo audit article.md
```

### Optimize Content

```bash
# Optimize a file
aieo optimize article.md

# Save to output file
aieo optimize article.md --output optimized.md

# Show diff
aieo optimize article.md --diff

# Aggressive optimization
aieo optimize article.md --style aggressive
```

### Dashboard

```bash
# View dashboard
aieo dashboard

# JSON output
aieo dashboard --json
```

## Configuration

Set environment variables:

- `AIEO_API_KEY`: Your API key
- `AIEO_API_URL`: API base URL (default: http://localhost:8000/api/v1)


