# 🧪 OpenCode Platform - Test Examples Guide

## 📋 Comprehensive Test Questions by Mode

### 1️⃣ Chat Mode - General Conversation
Simple, everyday queries that require straightforward answers:

**Basic Questions:**
- "What is the weather like today?"
- "How do you make scrambled eggs?"
- "What's the capital of France?"
- "Can you tell me a joke?"

**Explanations:**
- "Explain photosynthesis to a 10-year-old"
- "What is blockchain in simple terms?"
- "How does a car engine work?"
- "Why is the sky blue?"

**Advice & Recommendations:**
- "What are some tips for better sleep?"
- "How can I improve my productivity?"
- "What's a good book to read?"
- "How do I start learning programming?"

---

### 2️⃣ Thinking Mode - Deep Analysis
Complex questions requiring multi-step reasoning and critical thinking:

**Analytical Questions:**
- "Analyze the pros and cons of remote work vs office work"
- "What are the implications of quantum computing on cryptography?"
- "Evaluate the impact of social media on democracy"
- "Compare Eastern and Western philosophical approaches to happiness"

**Logic & Reasoning:**
- "If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets?"
- "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?"
- "What's the flaw in this argument: 'All birds can fly. Penguins are birds. Therefore, penguins can fly.'"
- "Solve: You have 12 balls, one is heavier. Find it using a balance scale in 3 weighings."

**Strategic Analysis:**
- "What strategies should a startup use to compete with established companies?"
- "Analyze the game theory behind prisoner's dilemma"
- "How might AI change education in the next 10 years?"
- "What are the second-order effects of universal basic income?"

---

### 3️⃣ Knowledge Mode - Information Retrieval
Questions requiring specific knowledge or expertise:

**Scientific Knowledge:**
- "Explain the mechanism of CRISPR gene editing"
- "What is the Standard Model of particle physics?"
- "How do vaccines work at the molecular level?"
- "Describe the process of nuclear fusion"

**Technical Knowledge:**
- "What are the SOLID principles in software design?"
- "Explain the CAP theorem in distributed systems"
- "How does TCP congestion control work?"
- "What is the difference between supervised and unsupervised learning?"

**Academic Topics:**
- "Summarize Kant's categorical imperative"
- "Explain the causes of the 2008 financial crisis"
- "What is the significance of the Turing test?"
- "Describe the structure of DNA and RNA"

---

### 4️⃣ Search Mode - Current Information
Questions requiring up-to-date information from the web:

**Current Events:**
- "What are today's top technology news?"
- "Latest updates on climate change policies"
- "Current COVID-19 statistics worldwide"
- "Recent developments in the Ukraine situation"

**Market Information:**
- "Current Bitcoin price and trend analysis"
- "Tesla stock performance this month"
- "Latest iPhone model specifications and price"
- "Top performing stocks in 2024"

**Real-time Data:**
- "Weather forecast for New York this week"
- "Flight prices from London to Tokyo"
- "Latest sports scores and standings"
- "Trending topics on social media today"

---

### 5️⃣ Code Mode - Programming Tasks
Programming-related questions and code generation:

**Code Generation:**
```python
"Write a Python function to find all prime numbers up to n"
"Create a binary search tree implementation in JavaScript"
"Generate a REST API endpoint in FastAPI for user authentication"
"Write a SQL query to find the second highest salary"
```

**Code Debugging:**
```python
"Debug this Python code:
def factorial(n):
    if n = 0:
        return 1
    else:
        return n * factorial(n)"
```

**Code Optimization:**
```python
"Optimize this bubble sort implementation"
"Improve the time complexity of this function"
"Refactor this code to follow SOLID principles"
"Convert this recursive solution to iterative"
```

**Algorithm Challenges:**
- "Implement Dijkstra's shortest path algorithm"
- "Write a function to detect cycles in a linked list"
- "Create a LRU cache with O(1) operations"
- "Solve the N-Queens problem"

---

### 6️⃣ Research Mode - Comprehensive Studies
Topics requiring extensive research and detailed reports:

**Technology Research:**
- "Research the current state and future of quantum computing"
- "Comprehensive analysis of blockchain applications beyond cryptocurrency"
- "Study on the evolution of artificial intelligence from 1950 to present"
- "Impact of 5G technology on various industries"

**Social Research:**
- "Effects of remote work on company culture and productivity"
- "Analysis of income inequality in developed nations"
- "Impact of social media on teenage mental health"
- "Study on the effectiveness of different education systems worldwide"

**Business Research:**
- "Competitive analysis of the electric vehicle market"
- "Research on sustainable business practices and their ROI"
- "Analysis of subscription economy business models"
- "Study on the gig economy's impact on traditional employment"

**Scientific Research:**
- "Current progress in fusion energy research"
- "Analysis of different approaches to carbon capture"
- "Research on potential solutions to antibiotic resistance"
- "Study on the possibility of life on exoplanets"

---

## 🎯 Testing Strategy

### For Quick Testing:
1. **Start with Chat mode** - Simple questions to verify basic functionality
2. **Move to Thinking mode** - Test reasoning capabilities
3. **Try Search mode** - Verify web search integration
4. **Test Code mode** - Check code generation quality

### For Comprehensive Testing:
1. Test each mode with at least 3 different types of questions
2. Try edge cases (very long queries, special characters, etc.)
3. Test mode switching during conversation
4. Verify response quality and formatting
5. Check error handling with invalid inputs

### Performance Benchmarks:
- **Chat mode**: Response in <2 seconds
- **Thinking mode**: Deep analysis in <10 seconds
- **Knowledge mode**: Retrieval in <3 seconds
- **Search mode**: Web results in <5 seconds
- **Code mode**: Generation in <5 seconds
- **Research mode**: Full report in <30 seconds

---

## 💡 Tips for Effective Testing

1. **Vary Question Complexity**: Start simple, gradually increase complexity
2. **Test Follow-up Questions**: Verify context retention
3. **Mix Languages**: Test with questions in different languages
4. **Check Edge Cases**: Very short/long queries, special characters
5. **Verify Citations**: In research/search modes, check source attribution
6. **Test Error Recovery**: Invalid commands, network issues
7. **Monitor Performance**: Track response times and token usage
8. **Validate Output Format**: Ensure proper Markdown rendering

## 🔍 Expected Behaviors

### Chat Mode:
- Quick, conversational responses
- Natural language understanding
- Context awareness within session

### Thinking Mode:
- Structured analysis with clear steps
- Multiple perspectives considered
- Logical reasoning displayed
- Self-reflection and validation

### Knowledge Mode:
- Accurate information retrieval
- Proper citations when applicable
- Comprehensive explanations
- Technical accuracy

### Search Mode:
- Current information
- Multiple sources considered
- Clear source attribution
- Relevance to query

### Code Mode:
- Syntactically correct code
- Proper comments and documentation
- Best practices followed
- Multiple language support

### Research Mode:
- Comprehensive reports
- Structured sections
- Multiple perspectives
- Proper citations
- Visual aids (charts/graphs) when applicable