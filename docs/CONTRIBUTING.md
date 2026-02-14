# Contributing to OpenCode Platform

Thank you for your interest in contributing to OpenCode Platform! We welcome contributions from the community.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Community](#community)

---

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code.

### Our Standards

- **Be Respectful**: Treat everyone with respect and consideration
- **Be Collaborative**: Work together constructively
- **Be Professional**: Focus on technical merit, not personal attacks
- **Be Inclusive**: Welcome contributors from all backgrounds

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Personal attacks or trolling
- Publishing others' private information
- Any conduct that would be considered inappropriate in a professional setting

**Reporting**: Email conduct@opencode.ai for any concerns.

---

## Getting Started

### Prerequisites

- **Python** 3.10 or higher
- **Git** for version control
- **Docker** (optional, for testing sandbox features)
- **GitHub account**

### Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/openagent_backend.git
cd openagent_backend

# Add upstream remote
git remote add upstream https://github.com/your-org/openagent_backend.git
```

### Development Environment Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Copy environment template
cp .env.example .env
# Edit .env and add your API keys
```

### Verify Installation

```bash
# Run tests
pytest tests/ -v

# Start CLI
python main.py

# Start API server
cd src && python -c "
import uvicorn
from api.routes import create_app
from core.engine import RefactoredEngine
from services.llm.openai_client import OpenAILLMClient
import os

llm = OpenAILLMClient(api_key=os.getenv('OPENAI_API_KEY'))
engine = RefactoredEngine(llm_client=llm)
app = create_app(engine=engine)
uvicorn.run(app, host='0.0.0.0', port=8000)
"
```

---

## Development Workflow

### 1. Create a Feature Branch

```bash
# Update your fork
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### Branch Naming Convention

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions or fixes
- `chore/` - Maintenance tasks

### 2. Make Your Changes

Follow our [Coding Standards](#coding-standards) and ensure all tests pass.

### 3. Commit Your Changes

We use [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Format: <type>(<scope>): <subject>

git commit -m "feat(processors): add custom processor registration API"
git commit -m "fix(llm): resolve timeout in multi-provider fallback"
git commit -m "docs(readme): add performance benchmarks section"
git commit -m "test(router): add complexity analyzer edge cases"
```

**Commit Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### 4. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

---

## Coding Standards

### Linus Torvalds Philosophy

We follow Linus Torvalds' principles for clean, maintainable code:

**1. Good Taste - Eliminate Special Cases**
```python
# ❌ Bad - Special cases
if mode == "chat":
    level = "system1"
elif mode == "search":
    level = "system2"
elif mode == "deep_research":
    level = "agent"

# ✅ Good - Data self-containment
@dataclass(frozen=True)
class ProcessingMode:
    name: str
    cognitive_level: str  # Data contains its own metadata

mode = ProcessingMode("chat", "system1")
level = mode.cognitive_level  # No special cases
```

**2. Simplicity - Functions ≤50 lines**
```python
# ❌ Bad - 200-line monster function
def process_everything(request):
    # ... 200 lines of mixed concerns

# ✅ Good - Small, focused functions
def process(request):
    validated = validate_request(request)
    mode = select_mode(validated)
    result = execute_processor(mode, validated)
    return format_response(result)
```

**3. No Deep Nesting - Indentation ≤3 levels**
```python
# ❌ Bad - 5 levels of indentation
def bad_function():
    if condition1:
        if condition2:
            for item in items:
                if item.valid:
                    if item.process():
                        ...  # 5 levels deep

# ✅ Good - Early returns, flat structure
def good_function():
    if not condition1:
        return
    if not condition2:
        return
    for item in items:
        if not item.valid:
            continue
        item.process()
```

### Python Style Guide

- **PEP 8 Compliance**: Use `black` for formatting
- **Line Length**: Maximum 100 characters
- **Type Hints**: All functions must have type annotations
- **Docstrings**: Use Google-style docstrings

```python
def process_request(
    request: Request,
    mode: ProcessingMode,
    context: Optional[ProcessingContext] = None
) -> Response:
    """Process a request using specified mode.

    Args:
        request: The incoming request object
        mode: Processing mode to use
        context: Optional processing context

    Returns:
        Response object with results

    Raises:
        ValidationError: If request is invalid
        ProcessorError: If processing fails
    """
    pass
```

### File Organization

- **Files ≤500 lines**: Split into multiple files if exceeded
- **Single Responsibility**: One class/concept per file
- **Consistent Naming**:
  - Files: `snake_case.py`
  - Classes: `PascalCase`
  - Functions/Variables: `snake_case`
  - Constants: `UPPER_SNAKE_CASE`

### Import Order

```python
# 1. Standard library
import os
from typing import Optional, Dict

# 2. Third-party
from fastapi import FastAPI
from pydantic import BaseModel

# 3. Local imports
from src.core.models import Request, Response
from src.services.llm import OpenAIClient
```

---

## Testing Guidelines

### Test Coverage Requirements

- **New Features**: ≥80% coverage
- **Bug Fixes**: Add regression test
- **Refactoring**: Maintain existing coverage

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_models_v2.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run only fast tests (skip integration)
pytest tests/unit/ -v
```

### Writing Tests

**Unit Tests** (fast, isolated):
```python
def test_processing_mode_creation():
    """Test ProcessingMode dataclass creation."""
    mode = ProcessingMode(
        name="chat",
        cognitive_level="system1",
        runtime_type=RuntimeType.MODEL,
        description="Chat mode"
    )

    assert mode.name == "chat"
    assert mode.cognitive_level == "system1"
    assert mode.runtime_type == RuntimeType.MODEL
```

**Integration Tests** (with real services):
```python
def test_multi_provider_fallback(openai_client, anthropic_client):
    """Test fallback chain when primary provider fails."""
    multi = MultiProviderLLMClient(
        providers=[openai_client, anthropic_client]
    )

    # Simulate OpenAI failure
    openai_client.should_fail = True

    result = multi.generate("Test prompt")
    assert result.provider == "Anthropic"  # Fallback worked
```

**End-to-End Tests** (full system):
```python
def test_auto_mode_routing_e2e(test_client):
    """Test auto mode correctly routes simple query to System 1."""
    response = test_client.post("/api/v1/chat", json={
        "query": "Hello",
        "mode": "auto"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["selected_mode"] == "chat"
    assert data["cognitive_level"] == "system1"
```

### Test Naming Convention

```python
# Pattern: test_<what>_<condition>_<expected>

def test_router_simple_query_selects_system1():
    pass

def test_processor_invalid_input_raises_validation_error():
    pass

def test_cache_expired_entry_returns_none():
    pass
```

---

## Pull Request Process

### Before Submitting

- [ ] All tests pass (`pytest tests/ -v`)
- [ ] Code coverage ≥80% for new code
- [ ] Code formatted with `black` (`black src/ tests/`)
- [ ] Type checking passes (`mypy src/`)
- [ ] No linting errors (`flake8 src/`)
- [ ] Documentation updated (if needed)
- [ ] CHANGELOG.md updated (if user-facing change)

### PR Title Format

Use Conventional Commits format:

```
feat(processors): add custom processor registration API
fix(llm): resolve timeout in multi-provider fallback
docs(readme): add performance benchmarks section
```

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## How Has This Been Tested?
- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual testing

## Checklist
- [ ] My code follows the project's coding standards
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests, linting, type checking
2. **Code Review**: Maintainer reviews code (typically 1-3 business days)
3. **Feedback**: Address review comments by pushing new commits
4. **Approval**: Once approved, maintainer will merge

### After Merge

- Delete your feature branch
- Update your fork's main branch
- Check if your contribution is listed in [CONTRIBUTORS.md](CONTRIBUTORS.md)

---

## Project Structure for Contributors

```
openagent_backend/
├── src/
│   ├── core/                 # Core engine logic
│   │   ├── engine.py         # Main engine
│   │   ├── router.py         # Request routing
│   │   ├── models_v2.py      # Data models (add new modes here)
│   │   ├── processors/       # Add custom processors here
│   │   │   ├── base.py       # Extend this for new processors
│   │   │   └── factory.py    # Register processors here
│   │   └── runtime/          # Runtime implementations
│   ├── services/             # External services
│   │   ├── llm/              # Add new LLM providers here
│   │   ├── knowledge/        # RAG implementation
│   │   └── search/           # Search integrations
│   └── api/                  # REST API
│       └── routes.py         # Add new endpoints here
├── tests/
│   ├── unit/                 # Add unit tests here
│   ├── integration/          # Add integration tests here
│   └── e2e/                  # Add end-to-end tests here
└── docs/                     # Documentation
```

### Common Contribution Areas

**1. Adding a New LLM Provider**

Location: `src/services/llm/`

```python
# 1. Create new provider file
# src/services/llm/cohere_client.py

from .base import LLMProvider
from .errors import ProviderError

class CohereLLMClient(LLMProvider):
    def generate(self, prompt: str, **kwargs) -> str:
        # Implementation
        pass

# 2. Register in multi_provider.py
providers = [
    OpenAIClient(),
    AnthropicClient(),
    GeminiClient(),
    CohereLLMClient(),  # Add here
]

# 3. Add tests
# tests/unit/test_cohere_client.py
```

**2. Adding a Custom Processor**

Location: `src/core/processors/`

```python
# 1. Create processor file
# src/core/processors/translation.py

from .base import BaseProcessor
from ..models import ProcessingMode, RuntimeType

class TranslationProcessor(BaseProcessor):
    def process(self, request):
        # Implementation
        pass

# 2. Register in factory.py
TRANSLATION = ProcessingMode(
    name="translation",
    cognitive_level="system1",
    runtime_type=RuntimeType.MODEL,
    description="Language translation"
)

_processors = {
    # ...
    ProcessingMode.TRANSLATION: TranslationProcessor,
}

# 3. Add tests
# tests/unit/test_translation_processor.py
```

**3. Adding a New API Endpoint**

Location: `src/api/routes.py`

```python
# Add endpoint
@app.post("/api/v1/translate")
async def translate_text(
    request: TranslateRequest,
    current_user: str = Depends(get_current_user)
):
    """Translate text between languages."""
    result = engine.process(Request(
        query=request.text,
        mode="translation",
        user_id=current_user
    ))
    return result

# Add tests
# tests/integration/test_api.py
def test_translate_endpoint_success(test_client):
    response = test_client.post("/api/v1/translate", json={
        "text": "Hello",
        "target_lang": "es"
    })
    assert response.status_code == 200
```

---

## Community

### Communication Channels

- **GitHub Discussions**: [Questions & Ideas](https://github.com/your-org/openagent_backend/discussions)
- **GitHub Issues**: [Bug Reports & Feature Requests](https://github.com/your-org/openagent_backend/issues)
- **Email**: dev@opencode.ai

### Getting Help

- Read the [README.md](README.md) and [documentation](https://docs.opencode.ai)
- Search [existing issues](https://github.com/your-org/openagent_backend/issues)
- Ask in [GitHub Discussions](https://github.com/your-org/openagent_backend/discussions)
- Join our community meetings (announced in Discussions)

### Recognition

All contributors are recognized in:
- [CONTRIBUTORS.md](CONTRIBUTORS.md)
- GitHub contributor graph
- Release notes (for significant contributions)

---

## Questions?

If you have questions about contributing, feel free to:
- Open a [Discussion](https://github.com/your-org/openagent_backend/discussions)
- Email: dev@opencode.ai

Thank you for contributing to OpenCode Platform! 🎉
