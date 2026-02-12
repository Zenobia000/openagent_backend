# Exa API Integration Guide

## Overview

OpenCode Platform now supports **Exa API** - a neural search engine that provides semantic understanding and high-quality search results for coding, research, news, and more.

## Features

### 🧠 Neural Search
- Semantic understanding of queries
- Context-aware results
- Multi-category search support

### 🎯 Search Types
- **Auto** (Default): Balanced relevance and speed (~1 second)
- **Fast**: Real-time applications, autocomplete
- **Neural**: Deep semantic search

### 📚 Content Categories
- **Code**: GitHub, StackOverflow, developer resources
- **Research Papers**: Academic papers from arXiv, PapersWithCode
- **News**: Real-time news articles
- **People**: Find professionals by expertise
- **Companies**: Company information and profiles
- **Tweets**: Social media discussions

## Setup

### 1. Get Your API Key

Visit [Exa Dashboard](https://dashboard.exa.ai) to get your API key.

### 2. Configure Environment

Add to your `.env` file:

```env
# Exa Search Configuration
EXA_API_KEY=your-exa-api-key-here
EXA_SEARCH_TYPE=auto  # auto, fast, neural
EXA_MAX_RESULTS=10
EXA_CONTENT_TYPE=text  # text, highlights
EXA_MAX_CHARACTERS=20000
```

### 3. Update Search Configuration

Configure Exa in your search fallback chain:

```env
# Primary provider
SEARCH_PRIMARY_PROVIDER=exa  # or keep tavily

# Fallback chain (Exa as fallback)
SEARCH_FALLBACK_CHAIN=exa,serper,brave,duckduckgo
```

## Usage

### Basic Search

```python
from services.search.exa_search import ExaSearchService

# Initialize service
exa = ExaSearchService()

# Basic search
results = await exa.search(
    query="React hooks best practices 2024",
    search_type="auto",
    num_results=10
)

for result in results:
    print(f"{result.title}: {result.url}")
```

### Category-Specific Search

```python
# Search for code examples
code_results = await exa.search_code(
    query="Python async await patterns",
    language="python",
    num_results=10
)

# Search research papers
papers = await exa.search_research(
    query="transformer architecture improvements",
    num_results=10
)

# Search latest news
news = await exa.search_news(
    query="OpenAI announcements",
    num_results=10,
    max_age_hours=24
)

# Search for people
people = await exa.search_people(
    query="machine learning engineer",
    num_results=10
)

# Search companies
companies = await exa.search_companies(
    query="AI startup healthcare",
    num_results=10
)
```

### Deep Research Integration

The enhanced DeepResearchProcessor automatically uses Exa when configured:

```python
from core.enhanced_deep_research import (
    EnhancedDeepResearchProcessor,
    SearchEngineConfig,
    SearchProviderType
)

# Configure with Exa as primary
config = SearchEngineConfig(
    primary=SearchProviderType.EXA,
    fallback_chain=[
        SearchProviderType.TAVILY,
        SearchProviderType.SERPER,
        SearchProviderType.MODEL
    ],
    max_results=10
)

processor = EnhancedDeepResearchProcessor(
    search_config=config
)

# Exa will automatically be used for searches
result = await processor.process(context)
```

## Function Calling / Tool Use

### OpenAI Integration

```python
from services.search.exa_search import ExaToolUse, ExaSearchService

# Get tool definition
tool = ExaToolUse.get_tool_definition()

# Add to OpenAI tools
tools = [tool]

# When tool is called
if tool_call.function.name == "exa_search":
    exa = ExaSearchService()
    result = await ExaToolUse.execute_tool_call(
        exa,
        json.loads(tool_call.function.arguments)
    )
```

### Anthropic Integration

```python
# Define tool for Claude
exa_tool = {
    "name": "exa_search",
    "description": "Search the web using Exa's neural search",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "category": {"type": "string"},
            "num_results": {"type": "integer"}
        },
        "required": ["query"]
    }
}

# Execute when called
if tool_use.name == "exa_search":
    result = await exa.search(**tool_use.input)
```

## Content Options

### Full Text vs Highlights

| Type | Config | Use Case |
|------|--------|----------|
| **Full Text** | `use_full_text=True, max_characters=20000` | Complete articles, documentation, code |
| **Highlights** | `use_full_text=False, max_characters=2000` | Summaries, snippets, lower token usage |

### Content Freshness

Control content age with `max_age_hours`:

```python
# Always get fresh content (livecrawl)
results = await exa.search(
    query="breaking news AI",
    max_age_hours=0  # Force livecrawl
)

# Use cache if less than 24 hours old
results = await exa.search(
    query="React documentation",
    max_age_hours=24
)

# Never livecrawl (cache only, fastest)
results = await exa.search(
    query="historical events",
    max_age_hours=-1
)
```

## Advanced Features

### Domain Filtering

```python
# Include specific domains
results = await exa.search(
    query="machine learning",
    include_domains=["arxiv.org", "github.com"]
)

# Exclude domains
results = await exa.search(
    query="python tutorial",
    exclude_domains=["pinterest.com", "instagram.com"]
)
```

### Date Filtering

```python
# Recent content only
results = await exa.search(
    query="AI developments",
    start_published_date="2024-01-01",
    end_published_date="2024-12-31"
)
```

### Get Content from URLs

```python
# Extract content from specific URLs
urls = [
    "https://example.com/article1",
    "https://example.com/article2"
]

contents = await exa.get_contents(
    urls=urls,
    use_full_text=True,
    max_characters=20000
)
```

## Performance Tips

### 1. Choose the Right Search Type
- **`auto`**: Best for most queries (balanced)
- **`fast`**: For real-time applications
- **`neural`**: When accuracy is critical

### 2. Optimize Content Extraction
- Use `highlights` instead of `text` when full content isn't needed
- Set reasonable `max_characters` limits
- Use `max_age_hours` to control caching

### 3. Category-Specific Searches
- Use categories to search dedicated indexes
- More accurate results for specific content types
- Faster than general search

### 4. Batch Searches
- Use parallel searches for multiple queries
- Leverage the `parallel_searches` configuration
- Monitor rate limits

## Error Handling

The integration includes comprehensive error handling:

```python
try:
    results = await exa.search(query="test")
except Exception as e:
    # Automatic fallback to next provider
    # Error logged with context
    pass
```

## Monitoring

Check logs for Exa-specific events:

```bash
# Exa search logs
grep "exa" logs/opencode.log

# Performance metrics
grep "exa.*timing" logs/opencode.log

# Error tracking
grep "exa.*error" logs/opencode.log
```

## Cost Management

Exa pricing is based on API calls. To optimize costs:

1. Use caching when appropriate
2. Set reasonable `num_results` limits
3. Use `highlights` instead of full text when possible
4. Monitor usage in Exa Dashboard

## Troubleshooting

### No Results
1. Check API key configuration
2. Verify network connectivity
3. Try with `search_type="auto"`
4. Remove category filters

### Slow Performance
1. Use `search_type="fast"`
2. Reduce `num_results`
3. Use highlights instead of full text
4. Check network latency

### Rate Limiting
1. Implement exponential backoff
2. Use the fallback chain
3. Contact Exa support for limit increases

## Resources

- [Exa Documentation](https://docs.exa.ai)
- [API Reference](https://docs.exa.ai/reference)
- [Dashboard](https://dashboard.exa.ai)
- [Status Page](https://status.exa.ai)