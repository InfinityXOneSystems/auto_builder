# AUTO_BUILDER - Development Setup Guide

## Prerequisites

- Python 3.9+
- pip/poetry package manager
- Git
- Docker (optional)
- GCP service account (for testing)

## Quick Start (5 minutes)

### 1. Clone Repository
```bash
git clone https://github.com/infinityxai/auto_builder.git
cd auto_builder
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Setup Environment
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 5. Run Development Server
```bash
python -m uvicorn src.main:app --reload --port 8000
```

Visit: http://localhost:8000/docs

## Full Setup Guide

### Step 1: Environment Setup

#### macOS/Linux
```bash
# Install Python
brew install python@3.11

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate
```

#### Windows
```powershell
# Install Python from python.org

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 2: Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# Development dependencies
pip install -r requirements-dev.txt

# Pre-commit hooks
pre-commit install
```

### Step 3: Configuration

```bash
# Copy example env
cp .env.example .env

# Configure for development
cat > .env << EOF
ENV=development
LOG_LEVEL=debug
DATABASE_URL=sqlite:///dev.db
REDIS_URL=redis://localhost:6379/0
EOF
```

### Step 4: Database Setup

```bash
# Initialize database
python -m src.db init

# Run migrations
python -m src.db migrate

# Seed data (optional)
python -m src.db seed
```

### Step 5: Run Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_core.py

# With coverage
pytest --cov=src --cov-report=html
```

## Development Workflow

### Code Style
```bash
# Format code
black src/ tests/

# Lint code
pylint src/
mypy src/  # Type checking
```

### Pre-commit
```bash
# Automatic checks before commit
pre-commit run --all-files
```

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes
# ...

# Commit with message
git commit -m "feat: add new feature"

# Push to remote
git push origin feature/new-feature

# Create pull request
# ...
```

## Testing

### Unit Tests
```bash
pytest tests/unit/ -v
```

### Integration Tests
```bash
pytest tests/integration/ -v
```

### End-to-End Tests
```bash
pytest tests/e2e/ -v
```

### Coverage Report
```bash
pytest --cov=src --cov-report=term-missing
```

## Database Management

### Create Migration
```bash
# Alembic
alembic revision --autogenerate -m "Add new column"
```

### Apply Migration
```bash
alembic upgrade head
```

### Rollback Migration
```bash
alembic downgrade -1
```

## Debugging

### Print Debugging
```python
print(f"Debug: {variable}")
import logging
logger.debug("Debug message")
```

### Debugger (pdb)
```python
import pdb; pdb.set_trace()
```

### VSCode Debugging
Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Debug",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal"
    }
  ]
}
```

## Documentation

### Generate Docs
```bash
# Sphinx
cd docs
make html
```

### View Docs
```bash
open build/html/index.html
```

## Common Issues

### Issue: Import errors
**Solution**: Ensure virtual environment is activated and dependencies installed
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: Port already in use
**Solution**: Use different port
```bash
python -m uvicorn src.main:app --port 8001
```

### Issue: Database locked
**Solution**: Remove database and reinitialize
```bash
rm dev.db
python -m src.db init
```

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Python Style Guide (PEP 8)](https://pep8.org/)
- [Testing Best Practices](https://docs.pytest.org/)
- [Git Workflow](https://git-scm.com/book/en/v2)

---
**Last Updated**: 2025-12-11
**Version**: 1.0.0
