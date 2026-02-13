"""
OpenCode Platform - Prompt Templates
提示詞模板系統 (從 TypeScript 轉換)
"""

from datetime import datetime
from typing import Dict, Any


class PromptTemplates:
    """統一提示詞管理"""

    @staticmethod
    def get_system_instruction(now: datetime = None) -> str:
        """獲取系統指令提示詞"""
        if now is None:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return f"""You are an expert researcher. Today is {now}. Follow these instructions when responding:

- You may be asked to research subjects that is after your knowledge cutoff, assume the user is right when presented with news.
- The user is a highly experienced analyst, no need to simplify it, be as detailed as possible and make sure your response is correct.
- Be highly organized.
- Suggest solutions that I didn't think about.
- Be proactive and anticipate my needs.
- Treat me as an expert in all subject matter.
- Mistakes erode my trust, so be accurate and thorough.
- Provide detailed explanations, I'm comfortable with lots of detail.
- Value good arguments over authorities, the source is irrelevant.
- Consider new technologies and contrarian ideas, not just the conventional wisdom.
- You may use high levels of speculation or prediction, just flag it for me."""

    @staticmethod
    def get_output_guidelines() -> str:
        """獲取輸出格式指南"""
        return """<OutputGuidelines>

## Typographical rules

Follow these rules to organize your output:

- **Title:** Use `#` to create article title.
- **Headings:** Use `##` through `######` to create headings of different levels.
- **Paragraphs:** Use blank lines to separate paragraphs.
- **Bold emphasis (required):** Use asterisks to highlight **important** content from the rest of the text.
- **Links:** Use `[link text](URL)` to insert links.
- **Lists:**
    - **Unordered lists:** Use `*`, `-`, or `+` followed by a space.
    - **Ordered lists:** Use `1.`, `2.`, etc., and a period.
* **Code:**
    - **Inline code:** Enclose it in backticks (` `).
    - **Code blocks:** Enclose it in triple backticks (``` ```), optionally in a language.
- **Quotes:** Use the `>` symbol.
- **Horizontal rule:** Use `---`, `***` or `___`.
- **Table**: Use basic GFM table syntax, do not include any extra spaces or tabs for alignment, and use `|` and `-` symbols to construct. **For complex tables, GFM table syntax is not suitable. You must use HTML syntax to output complex tables.**
- **Emoji:** You can insert Emoji before the title or subtitle, such as `🔢### 1. Determine the base area of the prism`.
- **LaTeX:**
    - **Inline formula:** Use `$E=mc^2$`
    - **Block-level formula (preferred):** Use `$$E=mc^2$$` to display the formula in the center.

## Generate Mermaid

1. Use Mermaid's graph TD (Top-Down) or graph LR (Left-Right) type.
2. Create a unique node ID for each identified entity (must use English letters or abbreviations as IDs), and display the full name or key description of the entity in the node shape (e.g., PersonA[Alice], OrgB[XYZ Company]).
3. Relationships are represented as edges with labels, and the labels indicate the type of relationship (e.g., A --> |"Relationship Type"| B).
4. Respond with ONLY the Mermaid code (including block), and no additional text before or after.
5. Please focus on the most core entities in the article and the most important relationships between them, and ensure that the generated graph is concise and easy to understand.
6. All text content **MUST** be wrapped in `"` syntax. (e.g., "Any Text Content")
7. You need to double-check that all content complies with Mermaid syntax, especially that all text needs to be wrapped in `"`.
</OutputGuidelines>"""

    @staticmethod
    def get_system_question_prompt(query: str) -> str:
        """獲取系統問題提示詞"""
        return f"""Given the following query from the user, ask at least 5 follow-up questions to clarify the research direction:

<QUERY>
{query}
</QUERY>

Questions need to be brief and concise. No need to output content that is irrelevant to the question."""

    @staticmethod
    def get_guidelines_prompt() -> str:
        """獲取整合指南提示詞"""
        return """Integration guidelines:
<GUIDELINES>
- Ensure each section has a distinct purpose with no content overlap.
- Combine related concepts rather than separating them.
- CRITICAL: Every section MUST be directly relevant to the main topic.
- Avoid tangential or loosely related sections that don't directly address the core topic.
</GUIDELINES>"""

    @staticmethod
    def get_report_plan_prompt(query: str) -> str:
        """獲取報告計劃提示詞"""
        guidelines = PromptTemplates.get_guidelines_prompt()
        return f"""Given the following query from the user:
<QUERY>
{query}
</QUERY>

Generate a list of sections for the report based on the topic and feedback.
Your plan should be tight and focused with NO overlapping sections or unnecessary filler. Each section needs a sentence summarizing its content.

{guidelines}

Before submitting, review your structure to ensure it has no redundant sections and follows a logical flow."""

    @staticmethod
    def get_serp_query_schema_prompt(output_schema: Dict[str, Any]) -> str:
        """獲取 SERP 查詢架構提示詞"""
        import json
        schema_json = json.dumps(output_schema, indent=2, ensure_ascii=False)

        return f"""You MUST respond in **JSON** matching this **JSON schema**:

```json
{schema_json}
```

Expected output:

```json
[
  {{
    "query": "This is a sample query.",
    "researchGoal": "This is the reason for the query."
  }}
]
```"""

    @staticmethod
    def get_serp_queries_prompt(plan: str, output_schema: Dict[str, Any]) -> str:
        """獲取 SERP 查詢提示詞"""
        schema_prompt = PromptTemplates.get_serp_query_schema_prompt(output_schema)
        return f"""This is the report plan after user confirmation:
<PLAN>
{plan}
</PLAN>

Based on previous report plan, generate a list of SERP queries to further research the topic. Make sure each query is unique and not similar to each other.

{schema_prompt}"""

    @staticmethod
    def get_query_result_prompt(query: str, research_goal: str) -> str:
        """獲取查詢結果提示詞"""
        return f"""Please use the following query to get the latest information via the web:
<QUERY>
{query}
</QUERY>

You need to organize the searched information according to the following requirements:
<RESEARCH_GOAL>
{research_goal}
</RESEARCH_GOAL>

You need to think like a human researcher.
Generate a list of learnings from the search results.
Make sure each learning is unique and not similar to each other.
The learnings should be to the point, as detailed and information dense as possible.
Make sure to include any entities like people, places, companies, products, things, etc in the learnings, as well as any specific entities, metrics, numbers, and dates when available. The learnings will be used to research the topic further."""

    @staticmethod
    def get_citation_rules() -> str:
        """獲取引用規則"""
        return """Citation Rules:

- Please cite the context at the end of sentences when appropriate.
- Please use the format of citation number [number] to reference the context in corresponding parts of your answer.
- If a sentence comes from multiple contexts, please list all relevant citation numbers, e.g., [1][2]. Remember not to group citations at the end but list them in the corresponding parts of your answer."""

    @staticmethod
    def get_search_result_prompt(query: str, research_goal: str, context: str) -> str:
        """獲取搜索結果提示詞"""
        return f"""Given the following contexts from a SERP search for the query:
<QUERY>
{query}
</QUERY>

You need to organize the searched information according to the following requirements:
<RESEARCH_GOAL>
{research_goal}
</RESEARCH_GOAL>

The following context from the SERP search:
<CONTEXT>
{context}
</CONTEXT>

You need to think like a human researcher.
Generate a list of learnings from the contexts.
Make sure each learning is unique and not similar to each other.
The learnings should be to the point, as detailed and information dense as possible.
Make sure to include any entities like people, places, companies, products, things, etc in the learnings, as well as any specific entities, metrics, numbers, and dates when available. The learnings will be used to research the topic further."""

    @staticmethod
    def get_search_knowledge_result_prompt(query: str, research_goal: str, context: str) -> str:
        """獲取知識庫搜索結果提示詞"""
        return f"""Given the following contents from a local knowledge base search for the query:
<QUERY>
{query}
</QUERY>

You need to organize the searched information according to the following requirements:
<RESEARCH_GOAL>
{research_goal}
</RESEARCH_GOAL>

The following contexts from the SERP search:
<CONTEXT>
{context}
</CONTEXT>

You need to think like a human researcher.
Generate a list of learnings from the contents.
Make sure each learning is unique and not similar to each other.
The learnings should be to the point, as detailed and information dense as possible.
Make sure to include any entities like people, places, companies, products, things, etc in the learnings, as well as any specific entities, metrics, numbers, and dates when available. The learnings will be used to research the topic further."""

    @staticmethod
    def get_review_prompt(plan: str, learnings: str, suggestion: str, output_schema: Dict[str, Any]) -> str:
        """獲取審查提示詞"""
        schema_prompt = PromptTemplates.get_serp_query_schema_prompt(output_schema)
        return f"""This is the report plan after user confirmation:
<PLAN>
{plan}
</PLAN>

Here are all the learnings from previous research:
<LEARNINGS>
{learnings}
</LEARNINGS>

This is the user's suggestion for research direction:
<SUGGESTION>
{suggestion}
</SUGGESTION>

Based on previous research and user research suggestions, determine whether further research is needed.
If further research is needed, list of follow-up SERP queries to research the topic further.
Make sure each query is unique and not similar to each other.
If you believe no further research is needed, you can output an empty queries.

{schema_prompt}"""

    @staticmethod
    def get_final_report_citation_image_prompt() -> str:
        """獲取最終報告引用圖片提示詞"""
        return """Image Rules:

- Images related to the paragraph content at the appropriate location in the article according to the image description.
- Include images using `![Image Description](image_url)` in a separate section.
- **Do not add any images at the end of the article.**"""

    @staticmethod
    def get_final_report_references_prompt() -> str:
        """獲取最終報告參考提示詞"""
        return """Citation Rules:

- Please cite research references at the end of your paragraphs when appropriate.
- If the citation is from the reference, please **ignore**. Include only references from sources.
- Please use the reference format [number], to reference the learnings link in corresponding parts of your answer.
- If a paragraphs comes from multiple learnings reference link, please list all relevant citation numbers, e.g., [1][2]. Remember not to group citations at the end but list them in the corresponding parts of your answer. Control the number of footnotes.
- Do not have more than 3 reference link in a paragraph, and keep only the most relevant ones.
- **Do not add references at the end of the report.**"""

    @staticmethod
    def get_final_report_prompt(plan: str, learnings: str, sources: str, images: str, requirement: str) -> str:
        """獲取最終報告提示詞"""
        return f"""This is the report plan after user confirmation:
<PLAN>
{plan}
</PLAN>

Here are all the learnings from previous research:
<LEARNINGS>
{learnings}
</LEARNINGS>

Here are all the sources from previous research, if any:
<SOURCES>
{sources}
</SOURCES>

Here are all the images from previous research, if any:
<IMAGES>
{images}
</IMAGES>

Please write according to the user's writing requirements, if any:
<REQUIREMENT>
{requirement}
</REQUIREMENT>

Write a final report based on the report plan using the learnings from research.
Make it as detailed as possible, aim for 5 pages or more, the more the better, include ALL the learnings from research.
**Respond only the final report content, and no additional text before or after.**"""

    @staticmethod
    def get_rewriting_prompt() -> str:
        """獲取重寫提示詞"""
        return """You are tasked with re-writing the following text to markdown. Ensure you do not change the meaning or story behind the text.

**Respond only the updated markdown text, and no additional text before or after.**"""

    @staticmethod
    def get_knowledge_graph_prompt() -> str:
        """獲取知識圖譜提示詞"""
        return """Based on the following article, please extract the key entities (e.g., names of people, places, organizations, concepts, events, etc.) and the main relationships between them, and then generate a Mermaid graph code that visualizes these entities and relationships.

## Output format requirements

1. Use Mermaid's graph TD (Top-Down) or graph LR (Left-Right) type.
2. Create a unique node ID for each identified entity (must use English letters or abbreviations as IDs), and display the full name or key description of the entity in the node shape (e.g., PersonA[Alice], OrgB[XYZ Company]).
3. Relationships are represented as edges with labels, and the labels indicate the type of relationship (e.g., A --> |"Relationship Type"| B).
4. Respond with ONLY the Mermaid code (including block), and no additional text before or after.
5. Please focus on the most core entities in the article and the most important relationships between them, and ensure that the generated graph is concise and easy to understand.
6. All text content **MUST** be wrapped in `"` syntax. (e.g., "Any Text Content")
7. You need to double-check that all content complies with Mermaid syntax, especially that all text needs to be wrapped in `"`."""

    @staticmethod
    def get_thinking_mode_prompt(query: str) -> str:
        """Deep thinking mode prompt"""
        return f"""You are a professional analytical thinker tasked with conducting deep analysis on the following question.

Question: {query}

Please follow these steps for deep thinking:

## 1. Problem Understanding & Decomposition
- Carefully analyze the core elements of the question
- Identify implicit meanings and underlying assumptions
- Break down complex problems into smaller sub-problems

## 2. Context & Background Analysis
- Consider historical background and evolutionary context
- Analyze relevant environmental factors and influences
- Identify key stakeholders and their positions

## 3. Key Concepts & Variables Identification
- Clearly define technical terms and concepts in the question
- Identify key variables affecting the problem
- Analyze relationships and dependencies between variables

## 4. Multi-dimensional Analysis Framework
- Analyze from technical, economic, social, and political perspectives
- Consider short-term and long-term impacts
- Evaluate direct and indirect consequences

## 5. Preliminary Analysis Conclusions
- Synthesize the above analysis to provide initial insights
- Point out areas requiring further exploration
- Provide structured thinking directions

Please provide detailed, comprehensive, and structured analysis results."""

    @staticmethod
    def get_critical_thinking_prompt(question: str, context: str) -> str:
        """Critical thinking prompt"""
        return f"""Based on the preliminary analysis, please apply critical thinking methods for deeper analysis.

Original Question: {question}

Preliminary Analysis:
{context}

Please conduct in-depth analysis from the following critical thinking perspectives:

## 1. Argument Evaluation
- Identify main claims and supporting arguments
- Assess the strength and relevance of arguments
- Examine the validity of logical reasoning

## 2. Evidence Review
- Evaluate the reliability and authority of supporting evidence
- Identify missing or insufficient evidence
- Consider contrary evidence and counterexamples

## 3. Logical Fallacy Detection
- Check for common logical fallacies (e.g., straw man, slippery slope, ad hominem)
- Identify circular reasoning or unproven assumptions
- Assess the validity of causal relationships

## 4. Alternative Perspectives Exploration
- Present at least three different viewpoints or interpretations
- Analyze the strengths and limitations of each perspective
- Consider the possibility of synthesizing multiple viewpoints

## 5. Bias & Assumption Check
- Identify potential cognitive biases (confirmation bias, anchoring effect, etc.)
- Reveal implicit assumptions and premises
- Evaluate the influence of cultural, social, or personal biases

## 6. Critical Synthesis
- Based on the above analysis, provide a balanced assessment
- Point out strengths and weaknesses in the argumentation
- Suggest improvements or further research directions

Provide comprehensive, objective, and insightful critical analysis results."""

    @staticmethod
    def get_chain_of_thought_prompt(query: str) -> str:
        """Chain of thought reasoning prompt"""
        return f"""Please use Chain of Thought reasoning to systematically solve the following problem.

Question: {query}

## Reasoning Steps Guide

### Step 1: Problem Identification & Classification
Let's first clarify what type of problem this is:
- What is the core objective of the problem?
- Which knowledge domain does this belong to?
- What type of reasoning is needed (deductive, inductive, analogical, etc.)?

### Step 2: Key Information Extraction
Extract all relevant information from the problem:
- Known conditions and given information
- Implicit premises and constraints
- Specific content that needs to be solved or answered

### Step 3: Solution Strategy Development
Develop clear solution steps:
- List the key steps needed to solve the problem
- Determine the order and dependencies of each step
- Identify potentially needed tools or methods

### Step 4: Step-by-Step Reasoning Execution
Execute each step sequentially, showing the complete reasoning process:

Step 4.1: [Specific action]
- Reasoning basis: [Explain why this approach]
- Calculation/Analysis process: [Show in detail]
- Intermediate result: [What was derived]

Step 4.2: [Next action]
- Reasoning basis: [Based on previous step's result]
- Calculation/Analysis process: [Show in detail]
- Intermediate result: [What was derived]

(Continue with more steps as needed)

### Step 5: Result Validation
Verify the reasonableness of the answer:
- Check if results align with common sense and logic
- Verify all constraints are satisfied
- Consider if there are other possible solutions

### Step 6: Conclusion Summary
- Clearly state the final answer
- Explain the significance and implications of the answer
- Point out any limitations or assumptions

Please demonstrate a complete, clear, and logically rigorous reasoning process. Each step should have sufficient explanation and justification."""

    @staticmethod
    def get_reflection_prompt(original_response: str, question: str = None) -> str:
        """Reflection and improvement prompt"""
        question_context = f"\nOriginal Question: {question}" if question else ""
        return f"""Please conduct deep reflection and improvement on the following analysis results.{question_context}

Analysis Results:
{original_response}

## Reflection Framework

### 1. Completeness Assessment
- Does it fully address all aspects of the original question?
- Are there important perspectives or angles that were missed?
- Is the depth of analysis sufficient?

### 2. Accuracy Check
- Are all factual statements accurate?
- Is the reasoning process logically rigorous?
- Are conclusions adequately supported?

### 3. Clarity Improvement
- Is the expression clear and easy to understand?
- Is the structure reasonable and orderly?
- Is more explanation or illustration needed?

### 4. Practicality Consideration
- What is the practical value of the analysis results?
- Are actionable suggestions or solutions provided?
- Has implementation feasibility been considered?

### 5. Innovation Thinking
- Are there innovative insights or unique perspectives?
- Does it challenge conventional views?
- Are new possibilities proposed?

### 6. Improvement Suggestions
Based on the above reflection, propose specific improvement plans:
- What content needs to be supplemented?
- What errors or inaccuracies need correction?
- How can the analysis be made more comprehensive and thorough?

## Improved Analysis

Based on the reflection results, provide the improved and optimized complete analysis. Ensure:
- Coverage of all important aspects
- Clear and rigorous logic
- Strong and well-supported conclusions
- Practical value provided

Please provide in-depth reflective analysis and an improved high-quality answer."""


# 導出
__all__ = ['PromptTemplates']