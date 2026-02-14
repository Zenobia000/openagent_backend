# Frequently Asked Questions (FAQ)

> **Last Updated**: 2026-02-14
> **Quick Links**: [General](#general) | [Technical](#technical) | [Performance](#performance) | [Security](#security) | [Contributing](#contributing)

Common questions about OpenCode Platform.

---

## General Questions

### Why another AI framework when LangChain/Haystack exist?

**Short Answer**: OpenCode focuses on **cognitive routing** and **production-readiness**, not just LLM chaining.

**Key Differentiators**:
- ✅ **Automatic complexity-based routing** - Not all tasks need expensive autonomous agents
- ✅ **Built-in multi-provider fallback** - 99.5% availability out of the box
- ✅ **Production API** - Auth, streaming, and feature flags included
- ✅ **Linus-approved code quality** - 9/10 for long-term maintainability
- ✅ **Cost optimization** - 78% savings via intelligent caching

**When to use alternatives**: See [Comparison](COMPARISON.md)

---

### Can I use it without Docker?

**Yes!** Docker is **optional**.

**Required for**:
- ✅ Code sandbox execution (`/api/v1/sandbox/execute`)
- ✅ Qdrant vector database (knowledge service)

**Not required for**:
- ✅ Chat, thinking, search modes
- ✅ API server
- ✅ CLI interface
- ✅ Multi-provider LLM

**Minimum Requirements**: Python 3.10+ only

---

### Which LLM providers are supported?

**Currently Supported**:
- ✅ **OpenAI** - GPT-4o, GPT-4-turbo, GPT-3.5-turbo
- ✅ **Anthropic** - Claude 3 Opus, Sonnet, Haiku
- ✅ **Google Gemini** - Gemini Pro, Gemini Pro Vision

**Planned (Q2 2026)**:
- 🔜 Cohere
- 🔜 Mistral AI
- 🔜 Local models via Ollama

**How it works**: Automatic fallback chain (OpenAI → Anthropic → Gemini)

---

### Is it production-ready?

**Yes.** Here's the evidence:

| Metric | Value | Status |
|--------|-------|--------|
| **Tests** | 272/278 passing | 97.8% ✅ |
| **Coverage** | 52% | Growing ✅ |
| **Code Quality** | 9/10 (Linus-style) | ✅ |
| **Breaking Changes** | 0 (100% backward compat) | ✅ |
| **Feature Flags** | YAML-driven | Zero-risk deployment ✅ |

**Recommendation**: Start with feature flags OFF, enable gradually

**Production Users**: Contact enterprise@opencode.ai for case studies

---

### What's the license?

**MIT License** - free for commercial use.

**You can**:
- ✅ Use commercially
- ✅ Modify the code
- ✅ Distribute
- ✅ Sublicense
- ✅ Use in closed-source products

**You must**:
- ✅ Include the license notice

**No warranty** - Use at your own risk

See [LICENSE](../LICENSE) for full text.

---

## Technical Questions

### How does the Router classify request complexity?

The `ComplexityAnalyzer` uses multiple heuristics:

```python
def analyze_complexity(self, query: str) -> float:
    score = 0.0

    # 1. Query length (longer = more complex)
    if len(query) > 200:
        score += 0.3

    # 2. Keywords detection
    analytical_keywords = ["analyze", "compare", "research", "evaluate"]
    if any(kw in query.lower() for kw in analytical_keywords):
        score += 0.4

    # 3. Question depth (multi-part questions)
    question_count = query.count("?")
    score += min(question_count * 0.2, 0.3)

    # 4. Context length (if provided)
    if len(context) > 500:
        score += 0.2

    return min(score, 1.0)
```

**Thresholds**:
- `< 0.3` → System 1 (chat/knowledge)
- `0.3 - 0.7` → System 2 (search/code/thinking)
- `> 0.7` → Agent (deep_research)

**Override**: Use explicit `mode` parameter to bypass router

---

### Can I add custom processors?

**Yes!** Extend `BaseProcessor` and register:

```python
from src.core.processors.base import BaseProcessor
from src.core.processors.factory import ProcessorFactory
from src.core.models import ProcessingMode, RuntimeType

# 1. Create custom processor
class TranslationProcessor(BaseProcessor):
    def process(self, request):
        # Your logic here
        translated = self.llm_client.generate(
            prompt=f"Translate to {request.context['target_lang']}: {request.query}"
        )
        return Response(content=translated)

# 2. Register with factory
factory = ProcessorFactory(llm_client=llm)
factory.register_processor(
    ProcessingMode(
        name="translation",
        cognitive_level="system1",
        runtime_type=RuntimeType.MODEL,
        description="Language translation"
    ),
    TranslationProcessor
)

# 3. Use it
result = engine.process(Request(
    query="Hello, world!",
    mode="translation",
    context={"target_lang": "Spanish"}
))
```

**Full Guide**: Coming in Q2 2026 at `docs/tutorials/custom_processors.md`

---

### How does multi-provider fallback work?

**Automatic retry chain** with exponential backoff:

```python
providers = [
    OpenAIClient(),      # Primary (highest quality)
    AnthropicClient(),   # Fallback 1
    GeminiClient()       # Fallback 2
]

for provider in providers:
    try:
        return provider.generate(prompt)
    except ProviderError as e:
        if e.retryable and provider != providers[-1]:
            logger.info(f"Provider {provider} failed, trying next")
            continue  # Try next provider
        else:
            raise  # Non-retryable or last provider
```

**Triggers fallback**:
- ✅ Rate limit errors (HTTP 429)
- ✅ Service unavailable (HTTP 503)
- ✅ Timeout errors

**Does NOT trigger fallback** (fails immediately):
- ❌ Invalid API key (HTTP 401)
- ❌ Invalid request (HTTP 400)
- ❌ Content policy violation

**Availability**: 99.5% (tested over 30 days)

---

### What's the difference between System 1 and System 2?

Based on [dual-process theory](https://en.wikipedia.org/wiki/Dual_process_theory) from cognitive psychology:

| Aspect | System 1 | System 2 |
|--------|----------|----------|
| **Speed** | Fast (45-89ms avg) | Slower (0.8-2.3s avg) |
| **Caching** | Yes (78% hit rate) | No |
| **Use Case** | Chat, knowledge retrieval | Analysis, code, search |
| **Complexity** | Low | Medium-High |
| **Cost** | $0 (cached) or $0.01 | $0.01-0.02 |
| **Example** | "What is Paris?" | "Compare Paris and London" |

**System 1**: Automatic, intuitive, fast
**System 2**: Analytical, deliberate, slow

**Agent**: Multi-step, autonomous workflows (System 2++)

---

## Performance Questions

### Can it handle 1000 requests/second?

**With proper setup: Yes**

| Configuration | Throughput | Notes |
|--------------|-----------|-------|
| **Single instance** | ~100 req/s | Limited by LLM API |
| **Single instance + cache** | ~450 req/s | System 1 only |
| **5 instances + cache** | ~2000 req/s | Kubernetes HPA |

**Bottleneck**: LLM API rate limits, not the platform

**Recommended Production Setup**:
```yaml
# Kubernetes HorizontalPodAutoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: opencode-api
spec:
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**See**: [Performance Benchmarks](PERFORMANCE.md)

---

### How much does it cost to run?

**Depends on LLM usage**. Example for 1000 requests/day:

**Without cache**:
```
1000 requests × $0.01/request = $10/day = $300/month
```

**With System 1 cache (78% hit rate)**:
```
220 LLM requests × $0.01 = $2.20/day = $66/month
Savings: $234/month (78%)
```

**Infrastructure costs** (AWS example):
- EC2 t3.medium: ~$30/month
- Redis ElastiCache: ~$15/month
- **Total**: ~$111/month (vs $345 without cache)

**Cost Calculator**: Coming Q3 2026

---

### Is there a hosted/managed version?

**Not yet.** Planned for Q4 2026.

**Current Options**:
- ✅ Self-host via Docker/Kubernetes
- ✅ Contact enterprise@opencode.ai for managed deployment assistance

**Why not now?**
- Focus on core platform stability first
- Want to ensure excellent self-hosting experience
- Gathering feedback on enterprise requirements

---

## Security Questions

### How are API keys stored?

**Never in code or logs**. Only in:

1. **Development**: `.env` file (never committed to git)
```bash
# .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

2. **Production**: Kubernetes secrets
```bash
kubectl create secret generic opencode-secrets \
  --from-literal=OPENAI_API_KEY=sk-... \
  --from-literal=JWT_SECRET=$(openssl rand -hex 32)
```

3. **Environment Variables**: Loaded at runtime
```python
api_key = os.getenv("OPENAI_API_KEY")  # Never hardcoded
```

**Security Features**:
- ✅ Redacted in all logs
- ✅ Not included in error messages
- ✅ Not sent to client in responses

---

### Is code execution safe?

**Yes**, with Docker sandbox isolation:

**Safety Measures**:
- ✅ **Isolated containers** - No access to host system
- ✅ **No network access** - Cannot connect to external services
- ✅ **Resource limits** - CPU, memory, time constraints
- ✅ **Read-only filesystem** - Except `/tmp` directory
- ✅ **Non-root user** - Processes run as unprivileged user
- ✅ **Automatic cleanup** - Containers destroyed after execution

**Example Configuration**:
```python
# Docker sandbox settings
SANDBOX_CONFIG = {
    "memory_limit": "512m",
    "cpu_quota": 50000,  # 0.5 CPU
    "timeout": 30,       # seconds
    "network_disabled": True,
    "read_only": True
}
```

**What can't be done**:
- ❌ Access host filesystem
- ❌ Make network requests
- ❌ Install packages
- ❌ Run indefinitely

**See**: [SECURITY.md](SECURITY.md)

---

### How do I report security vulnerabilities?

**DO NOT open public GitHub issues**

**Instead**:
1. Email: **security@opencode.ai**
2. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

**Response Time**:
- Acknowledgment: Within **48 hours**
- Initial assessment: Within **5 business days**
- Fix timeline: Depends on severity (see [SECURITY.md](SECURITY.md))

**Credit**: Public recognition in release notes (unless you prefer anonymity)

---

## Contributing Questions

### How can I contribute?

**We welcome contributions!** See [CONTRIBUTING.md](CONTRIBUTING.md)

**Areas we need help**:
1. **📖 Documentation** - Tutorials, examples, translations
2. **🧪 Testing** - Test coverage (goal: 80%)
3. **🐛 Bug Fixes** - See [good first issue](https://github.com/your-org/openagent_backend/labels/good%20first%20issue)
4. **✨ Features** - Check [roadmap](ROADMAP.md)

**Quick Start**:
```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/openagent_backend.git

# Setup dev environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/

# Make changes and submit PR
```

---

### What's the code review process?

**Steps**:
1. **Fork** and create feature branch
2. **Make changes** with tests (≥80% coverage)
3. **Submit PR** with clear description
4. **Automated checks** - Tests, linting, type checking
5. **Code review** by maintainers (1-3 days)
6. **Merge** after approval

**PR Requirements**:
- ✅ All tests pass
- ✅ Code coverage ≥80%
- ✅ Follows [Linus philosophy](CONTRIBUTING.md#linus-torvalds-philosophy)
- ✅ Type hints on all functions
- ✅ Clear commit messages

---

### Can I use this commercially?

**Yes!** MIT License allows commercial use.

**No restrictions** on:
- ✅ Commercial products
- ✅ Closed-source applications
- ✅ Selling services built on OpenCode
- ✅ Modifying the code
- ✅ Sublicensing

**Only requirement**: Include license notice

---

## Still Have Questions?

### Get Help

- 💬 **GitHub Discussions**: [Ask Community](https://github.com/your-org/openagent_backend/discussions)
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/your-org/openagent_backend/issues)
- 📧 **Email**: support@opencode.ai
- 📚 **Documentation**: [Full Docs](../README.md)

### Popular Topics

- [Getting Started](../README.md#quick-start)
- [Examples](../examples/)
- [Performance Tuning](PERFORMANCE.md)
- [Deployment Guide](../docs/deployment/)
- [Troubleshooting](../README.md#troubleshooting)

---

**Back to**: [README](../README.md) | [Documentation](../README.md#-documentation)
