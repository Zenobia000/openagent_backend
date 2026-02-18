"""
OpenCode Platform - Prompt Templates
提示詞模板系統 (從 TypeScript 轉換)
"""

from datetime import datetime
from typing import Dict, Any


def _sanitize_xml_input(text: str) -> str:
    """Escape XML-like tag delimiters to prevent prompt injection.

    User-provided content interpolated into XML-tagged prompt sections
    (e.g. <QUERY>...</QUERY>) can break out of the tag boundary if it
    contains raw '<' or '>' characters.  This function neutralises them.
    """
    if not isinstance(text, str):
        text = str(text)
    return text.replace("<", "&lt;").replace(">", "&gt;")


class PromptTemplates:
    """統一提示詞管理"""

    # Mode-specific instruction extensions
    _MODE_EXTENSIONS: Dict[str, str] = {
        "chat": """
- Be conversational and direct. Provide clear, actionable answers.
- Match response length to question complexity — brief for simple queries, detailed for complex ones.
- When uncertain, say so rather than guessing.""",

        "knowledge": """
- Ground your answers in the retrieved context provided. Cite specific passages when possible.
- If the retrieved context does not contain sufficient information, explicitly state what is missing.
- Clearly distinguish between information from the knowledge base and your own reasoning.""",

        "search": """
- Synthesize information from multiple web search results into a coherent answer.
- Cite sources using [number] format when presenting factual claims.
- Distinguish between verified information from sources and your own synthesis.""",

        "code": """
- Focus on generating correct, secure, executable code.
- Follow the language's idiomatic conventions and best practices.
- Consider edge cases, input validation, and potential security implications.
- Be concise — output code with minimal surrounding explanation unless asked.""",

        "thinking": """
- Conduct deep, multi-perspective analytical reasoning.
- Decompose complex problems into structured sub-problems.
- Consider alternative viewpoints and potential counterarguments.
- Provide a balanced assessment before drawing conclusions.""",

        "deep_research": """
- Conduct exhaustive, multi-step research with structured output.
- Maintain a clear evidence hierarchy: primary sources over secondary, recent over dated.
- Organize findings into a coherent report structure.
- Flag areas where evidence is insufficient or conflicting.""",
    }

    @staticmethod
    def get_system_instruction(mode: str = "auto", now: str = None) -> str:
        """獲取系統指令提示詞

        Args:
            mode: Processing mode — one of auto, chat, knowledge, search,
                  code, thinking, deep_research.  Selects mode-specific
                  behavioural extensions appended to the base instruction.
            now:  Current timestamp string.  If ``None``, uses
                  ``datetime.now()`` formatted as ``%Y-%m-%d %H:%M:%S``.
        """
        if now is None:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        base = f"""You are an expert AI assistant on the OpenCode platform. Today is {now}. Follow these instructions when responding:

- You may be asked about subjects after your knowledge cutoff; accept user-provided news as current information.
- Be highly organized with structured, well-formatted output.
- Be accurate and thorough — mistakes erode trust.
- Provide detailed explanations; the user is a knowledgeable professional.
- Suggest alternative approaches and consider contrarian ideas, not just conventional wisdom.
- Be proactive: anticipate follow-up questions and address them preemptively.

Evidence calibration:
- [VERIFIED] — established facts supported by reliable sources or retrieved context.
- [INFERRED] — logical conclusions drawn from available evidence; state your reasoning.
- [SPECULATIVE] — predictions or hypotheses; explicitly flag as speculation."""

        extension = PromptTemplates._MODE_EXTENSIONS.get(mode, "")
        if extension:
            return f"{base}\n{extension}"
        return base

    @staticmethod
    def get_code_generation_prompt(code_request: str) -> str:
        """Code generation prompt for CodeProcessor"""
        sanitized = _sanitize_xml_input(code_request)
        return f"""You are an expert programmer. Generate clean, correct, executable Python code for the following request.

Requirements:
- Write production-quality code with proper error handling
- Include necessary imports
- Add brief inline comments only where logic is non-obvious
- Output ONLY the code block, no surrounding explanation

<CODE_REQUEST>
{sanitized}
</CODE_REQUEST>"""

    @staticmethod
    def get_output_guidelines(include_mermaid: bool = False) -> str:
        """獲取輸出格式指南

        Args:
            include_mermaid: When ``True``, append Mermaid diagram generation
                rules.  Default ``False`` — most processing modes do not
                need Mermaid output formatting.
        """
        base = """<OutputGuidelines>

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
    - **Block-level formula (preferred):** Use `$$E=mc^2$$` to display the formula in the center."""

        mermaid_section = """

## Generate Mermaid

1. Use Mermaid's graph TD (Top-Down) or graph LR (Left-Right) type.
2. Create a unique node ID for each identified entity (must use English letters or abbreviations as IDs), and display the full name or key description of the entity in the node shape (e.g., PersonA[Alice], OrgB[XYZ Company]).
3. Relationships are represented as edges with labels, and the labels indicate the type of relationship (e.g., A --> |"Relationship Type"| B).
4. Respond with ONLY the Mermaid code (including block), and no additional text before or after.
5. Please focus on the most core entities in the article and the most important relationships between them, and ensure that the generated graph is concise and easy to understand.
6. All text content **MUST** be wrapped in `"` syntax. (e.g., "Any Text Content")
7. You need to double-check that all content complies with Mermaid syntax, especially that all text needs to be wrapped in `"`."""

        if include_mermaid:
            return f"{base}{mermaid_section}\n</OutputGuidelines>"
        return f"{base}\n</OutputGuidelines>"

    @staticmethod
    def get_system_question_prompt(query: str) -> str:
        """獲取系統問題提示詞"""
        q = _sanitize_xml_input(query)
        return f"""Given the following query from the user, ask at least 5 follow-up questions to clarify the research direction:

<QUERY>
{q}
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
        q = _sanitize_xml_input(query)
        guidelines = PromptTemplates.get_guidelines_prompt()
        return f"""Given the following query from the user:
<QUERY>
{q}
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
    def get_serp_queries_prompt(plan: str, output_schema: Dict[str, Any], query_budget: int = 8) -> str:
        """獲取 SERP 查詢提示詞 — budget-aware"""
        p = _sanitize_xml_input(plan)
        schema_prompt = PromptTemplates.get_serp_query_schema_prompt(output_schema)
        return f"""This is the report plan after user confirmation:
<PLAN>
{p}
</PLAN>

Generate exactly {query_budget} search queries to research this topic. Rules:
- Each query is a SHORT keyword phrase (3-8 words) optimized for search engines
- NOT a research question or full sentence. Example: "藍領平台 SaaS 轉型 2026" not "2026年藍領垂直領域平台如何進行服務轉型"
- Cover different aspects/domains proportionally
- Each query must be unique and target distinct information
- Prioritize queries by information density potential (highest priority = 1)

{schema_prompt}"""

    @staticmethod
    def get_query_result_prompt(query: str, research_goal: str) -> str:
        """獲取查詢結果提示詞"""
        q = _sanitize_xml_input(query)
        rg = _sanitize_xml_input(research_goal)
        return f"""Please use the following query to get the latest information via the web:
<QUERY>
{q}
</QUERY>

You need to organize the searched information according to the following requirements:
<RESEARCH_GOAL>
{rg}
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
        q = _sanitize_xml_input(query)
        rg = _sanitize_xml_input(research_goal)
        ctx = _sanitize_xml_input(context)
        return f"""Given the following contexts from a SERP search for the query:
<QUERY>
{q}
</QUERY>

You need to organize the searched information according to the following requirements:
<RESEARCH_GOAL>
{rg}
</RESEARCH_GOAL>

The following context from the SERP search:
<CONTEXT>
{ctx}
</CONTEXT>

You need to think like a human researcher.
Generate a list of learnings from the contexts.
Make sure each learning is unique and not similar to each other.
The learnings should be to the point, as detailed and information dense as possible.
Make sure to include any entities like people, places, companies, products, things, etc in the learnings, as well as any specific entities, metrics, numbers, and dates when available. The learnings will be used to research the topic further."""

    @staticmethod
    def get_search_knowledge_result_prompt(query: str, research_goal: str, context: str) -> str:
        """獲取知識庫搜索結果提示詞"""
        q = _sanitize_xml_input(query)
        rg = _sanitize_xml_input(research_goal)
        ctx = _sanitize_xml_input(context)
        return f"""Given the following contents from a local knowledge base search for the query:
<QUERY>
{q}
</QUERY>

You need to organize the searched information according to the following requirements:
<RESEARCH_GOAL>
{rg}
</RESEARCH_GOAL>

The following contexts from the SERP search:
<CONTEXT>
{ctx}
</CONTEXT>

You need to think like a human researcher.
Generate a list of learnings from the contents.
Make sure each learning is unique and not similar to each other.
The learnings should be to the point, as detailed and information dense as possible.
Make sure to include any entities like people, places, companies, products, things, etc in the learnings, as well as any specific entities, metrics, numbers, and dates when available. The learnings will be used to research the topic further."""

    @staticmethod
    def get_review_prompt(plan: str, learnings: str, suggestion: str,
                          output_schema: Dict[str, Any], remaining_budget: int = 5) -> str:
        """獲取審查提示詞 — budget-aware follow-up"""
        p = _sanitize_xml_input(plan)
        l = _sanitize_xml_input(learnings)
        s = _sanitize_xml_input(suggestion)
        schema_prompt = PromptTemplates.get_serp_query_schema_prompt(output_schema)
        return f"""This is the report plan after user confirmation:
<PLAN>
{p}
</PLAN>

Here are all the learnings from previous research:
<LEARNINGS>
{l}
</LEARNINGS>

This is the user's suggestion for research direction:
<SUGGESTION>
{s}
</SUGGESTION>

Based on previous research, determine whether further research is needed.
If further research is needed, generate at most {remaining_budget} follow-up queries to fill specific knowledge gaps.
Rules:
- Each query is a SHORT keyword phrase (3-8 words) for search engines
- Target ONLY the gaps not covered by existing learnings
- If no significant gaps remain, output an empty array []

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
        p = _sanitize_xml_input(plan)
        l = _sanitize_xml_input(learnings)
        src = _sanitize_xml_input(sources)
        img = _sanitize_xml_input(images)
        req = _sanitize_xml_input(requirement)
        return f"""This is the report plan after user confirmation:
<PLAN>
{p}
</PLAN>

Here are all the learnings from previous research:
<LEARNINGS>
{l}
</LEARNINGS>

Here are all the sources from previous research, if any:
<SOURCES>
{src}
</SOURCES>

Here are all the images from previous research, if any:
<IMAGES>
{img}
</IMAGES>

Please write according to the user's writing requirements, if any:
<REQUIREMENT>
{req}
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
        q = _sanitize_xml_input(query)
        return f"""You are a professional analytical thinker tasked with conducting deep analysis on the following question.

Question: {q}

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
        q = _sanitize_xml_input(question)
        ctx = _sanitize_xml_input(context)
        return f"""Based on the preliminary analysis, please apply critical thinking methods for deeper analysis.

Original Question: {q}

Preliminary Analysis:
{ctx}

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
    def get_computational_triage_prompt(query: str, research_summary: str) -> str:
        """Determine whether research findings warrant computational analysis."""
        q = _sanitize_xml_input(query)
        rs = _sanitize_xml_input(research_summary)
        return f"""You are a research analyst. Determine whether the following research findings contain quantitative data that would benefit from computational analysis (statistics, calculations, trend modeling, data visualization).

<QUERY>
{q}
</QUERY>

<RESEARCH_FINDINGS>
{rs}
</RESEARCH_FINDINGS>

Answer YES if the findings contain numerical data, percentages, time-series, comparisons, or metrics that can be meaningfully computed, verified, or visualized with code.
Answer NO if the findings are purely qualitative, conceptual, or lack concrete numbers.

Reply with ONLY "YES" or "NO" followed by a one-sentence reason."""

    @staticmethod
    def get_computational_analysis_prompt(query: str, research_summary: str, report_plan: str) -> str:
        """Generate Python code for computational analysis of research data."""
        q = _sanitize_xml_input(query)
        rs = _sanitize_xml_input(research_summary)
        rp = _sanitize_xml_input(report_plan)
        return f"""You are a data analyst. Based on the research findings below, write Python code that performs meaningful quantitative analysis.

<RESEARCH_QUESTION>
{q}
</RESEARCH_QUESTION>

<RESEARCH_PLAN>
{rp}
</RESEARCH_PLAN>

<RESEARCH_FINDINGS>
{rs}
</RESEARCH_FINDINGS>

Write a single Python script that:
1. Extracts or reconstructs numerical data mentioned in the research findings
2. Performs meaningful calculations (statistics, comparisons, trends, projections)
3. Creates clear visualizations (charts/graphs) using matplotlib or seaborn
4. Prints key quantitative findings using print()
5. Stores the final summary in a variable named `result`

Rules:
- Output ONLY a single ```python code block, no explanation
- Available libraries: numpy, scipy, sympy, pandas, matplotlib, seaborn, plotly, sklearn
- Do NOT use requests, urllib, or any network libraries
- Do NOT read or write files
- Use matplotlib.pyplot as plt for charts; call plt.tight_layout() before plt.show()
- Use plt.figure() to create separate figures for different analyses
- All data must come from the research findings above — hardcode the numbers
- Focus on computation that adds insight beyond what text alone provides
- If concrete numbers are sparse, create reasonable illustrative models based on available data
- Keep the code under 80 lines"""

    @staticmethod
    def get_chart_planning_prompt(query: str, research_summary: str, report_plan: str) -> str:
        """Plan specific charts to include in the report."""
        q = _sanitize_xml_input(query)
        rs = _sanitize_xml_input(research_summary)
        rp = _sanitize_xml_input(report_plan)
        return f"""You are a McKinsey-trained data visualization specialist.
Based on the research findings, identify 2-4 charts that would add analytical value to the report.

<QUERY>{q}</QUERY>
<REPORT_PLAN>{rp}</REPORT_PLAN>
<RESEARCH_FINDINGS>{rs}</RESEARCH_FINDINGS>

For each chart, specify:
- title: Descriptive chart title
- chart_type: one of bar, line, pie, heatmap, scatter, waterfall, or radar
- data_description: What specific data to extract from findings (be precise about numbers, categories, time periods)
- target_section: Which report section heading this chart belongs in (use exact heading text)
- insight: The key analytical takeaway this chart should reveal

Rules:
- Only propose charts where concrete numerical data exists in the research findings
- Each chart must reveal an insight that text alone cannot convey effectively
- Prefer comparative charts (bar, heatmap) over decorative ones (pie)
- Maximum 4 charts

Reply with ONLY a JSON block:
```json
{{"charts": [
  {{"title": "...", "chart_type": "...", "data_description": "...", "target_section": "...", "insight": "..."}}
]}}
```"""

    @staticmethod
    def get_single_chart_code_prompt(chart_spec: dict, research_summary: str) -> str:
        """Generate Python code for a single chart."""
        import json as _json
        spec_str = _json.dumps(chart_spec, ensure_ascii=False, indent=2)
        rs = _sanitize_xml_input(research_summary)
        return f"""Generate Python code for ONE chart. Output ONLY a ```python code block.

Chart specification:
{spec_str}

Research data to extract numbers from:
{rs}

Rules:
- Use matplotlib with plt.figure(figsize=(10, 6))
- Set Chinese font support: plt.rcParams['font.sans-serif'] = ['SimHei', 'Noto Sans CJK TC', 'DejaVu Sans']
- plt.rcParams['axes.unicode_minus'] = False
- Hardcode all data from research findings — no external data sources
- Call plt.tight_layout() then plt.show()
- Print a one-line insight summary via print()
- Keep under 40 lines
- Available: numpy, pandas, matplotlib, seaborn"""

    @staticmethod
    def get_intermediate_synthesis_prompt(query: str, report_plan: str,
                                          wave_results: str,
                                          previous_synthesis: str = None) -> str:
        """Progressive synthesis — integrate new findings with prior understanding."""
        q = _sanitize_xml_input(query)
        rp = _sanitize_xml_input(report_plan)
        wr = _sanitize_xml_input(wave_results) if isinstance(wave_results, str) else _sanitize_xml_input(str(wave_results))

        prev_block = ""
        if previous_synthesis:
            ps = _sanitize_xml_input(previous_synthesis)
            prev_block = f"""
<PREVIOUS_SYNTHESIS>
{ps}
</PREVIOUS_SYNTHESIS>

Integrate the new findings with your previous understanding. Update, correct, or deepen your synthesis."""

        return f"""You are a research analyst performing progressive synthesis. Integrate the latest search findings into a coherent understanding.

<RESEARCH_QUESTION>
{q}
</RESEARCH_QUESTION>

<REPORT_PLAN>
{rp}
</REPORT_PLAN>

<NEW_FINDINGS>
{wr}
</NEW_FINDINGS>
{prev_block}

Respond with a JSON object (no markdown fencing) containing:
{{
  "synthesis": "Updated comprehensive understanding integrating all findings so far",
  "section_coverage": {{
    "section_name": {{"status": "covered|partial|missing", "notes": "brief note"}}
  }},
  "knowledge_gaps": ["specific gap 1", "specific gap 2"],
  "cross_domain_links": ["connection between domain A and B"]
}}

Rules:
- synthesis: thorough paragraph summarizing current understanding
- section_coverage: evaluate each section from the report plan
- knowledge_gaps: specific questions or data points still missing
- cross_domain_links: connections between different fields identified in findings"""

    @staticmethod
    def get_completeness_review_prompt(report_plan: str, section_coverage: dict,
                                       iteration: int, max_iterations: int) -> str:
        """Structured completeness review — section-level evaluation."""
        rp = _sanitize_xml_input(report_plan)
        import json as _json
        sc = _sanitize_xml_input(_json.dumps(section_coverage, ensure_ascii=False, default=str))

        return f"""You are evaluating research completeness for a deep research report.

<REPORT_PLAN>
{rp}
</REPORT_PLAN>

<CURRENT_COVERAGE>
{sc}
</CURRENT_COVERAGE>

Current iteration: {iteration} / {max_iterations}

Evaluate whether the research is sufficient to write a comprehensive report. Consider:
1. Does every section in the plan have adequate source material?
2. Are there critical knowledge gaps that would weaken the report?
3. Is there enough data for cross-domain analysis?

Respond with a JSON object (no markdown fencing):
{{
  "is_sufficient": true or false,
  "overall_coverage": 0-100,
  "sections": [
    {{"name": "section name", "coverage": 0-100, "depth": "low|medium|high", "gaps": ["specific gap"]}}
  ],
  "priority_gaps": ["most important query direction to fill"]
}}

Rules:
- is_sufficient: true only if overall_coverage >= 70 and no section is below 40
- priority_gaps: 1-3 specific search directions that would most improve the report
- Be strict: partial coverage of key sections should result in is_sufficient=false"""

    @staticmethod
    def get_domain_identification_prompt(query: str, report_plan: str) -> str:
        """Identify research domains and search angles for multi-domain coverage."""
        q = _sanitize_xml_input(query)
        p = _sanitize_xml_input(report_plan)
        return f"""You are a research strategist. Analyze the following research query and plan, then identify the distinct knowledge domains involved and the best search angles for each.

Research Query: {q}

Report Plan:
{p}

Return a JSON object with this structure:
```json
{{
  "domains": [
    {{
      "name": "domain name (e.g. technology, business, economics, regulation, sociology)",
      "weight": 0.0-1.0,
      "search_angles": ["specific search angle 1", "specific search angle 2"]
    }}
  ]
}}
```

Rules:
- Identify 2-5 distinct domains
- Weights must sum to 1.0
- Each domain needs 2-4 specific search angles
- Search angles should be concrete enough to serve as search queries
- Consider cross-domain intersections (e.g. "regulatory impact on technology adoption")
- Return ONLY the JSON, no explanation"""

    @staticmethod
    def get_chain_of_thought_prompt(query: str) -> str:
        """Chain of thought reasoning prompt"""
        q = _sanitize_xml_input(query)
        return f"""Please use Chain of Thought reasoning to systematically solve the following problem.

Question: {q}

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
        resp = _sanitize_xml_input(original_response)
        question_context = f"\nOriginal Question: {_sanitize_xml_input(question)}" if question else ""
        return f"""Please conduct deep reflection and improvement on the following analysis results.{question_context}

Analysis Results:
{resp}

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