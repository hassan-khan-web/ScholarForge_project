# ScholarForge: AI Generation Engine

This chapter covers the core operations of report generation located in `backend/AI_engine.py` and `backend/report_formats.py`. These modules handle model selection, semantic search, web scraping, outline planning, data visualization, and document compilation.

---

## Model Selection and Fallback Strategy

The application leverages OpenRouter to access large language models:
* **Primary Model (`SMART_MODEL`)**: `google/gemini-2.0-flash-exp:free`.
* **Backup Model (`BACKUP_MODEL`)**: `nvidia/llama-3.1-nemotron-70b-instruct:free`.

To prevent crashes from API rate limits, server errors, or token limits, `call_llm` implements a **failover retry mechanism**:

```python
def call_llm(target_model: str, system_prompt: str, user_prompt: str, temp: float = 0.4, attempt: int = 1) -> str:
    current_model = target_model
    if attempt == 2:
        current_model = BACKUP_MODEL
        logger.info(f"Model Switch: {current_model}")
    elif attempt > 2:
        return "Error: AI models unavailable."
    ...
```

If the first attempt fails (non-200 status code or network exception), the function retries using the backup model.

---

## Output Cleaning and Sanitization

To ensure reports are properly formatted, the AI output is cleaned using two helper functions:

1. **`clean_ai_output(text)`**:
   * Uses regular expressions to remove internal reasoning tags (like `<think>...</think>`).
   * Strips markdown code blocks (e.g., ` ```markdown ` and ` ``` `) from the response, returning clean, raw text.

2. **`clean_section_output(text, section_title)`**:
   * Removes duplicate headers at the beginning of a section to prevent double-header artifacts (e.g., repeating the section title) when compiling the final report.

---

## Semantic Search & Web Scraping

ScholarForge collects external information using two components:

1. **Tavily Search API (`get_search_results`)**:
   Sends an optimized search query using the `SERP_KEY`. Tavily is configured for semantic search, returning a structured list of relevant web results (titles, URLs, and summaries).

2. **BeautifulSoup Scraper (`_get_article_text`)**:
   If deep-diving, it issues HTTP GET requests to retrieve full page contents. It strips scripts, style blocks, footers, navigation bars, and headers to extract clean body text, which is capped at 5,000 characters to conserve prompt space.

---

## Decision Engines

The generation engine uses two LLM-driven decision steps to optimize search behavior:

### 1. `assess_search_need`
Before searching, this step decides if external information is required:
* If the topic is conceptual (e.g., general science or history) or answered by the uploaded documents, it returns `SKIP_SEARCH`.
* If it requires real-time information or specific statistics, it returns an optimized search query.

### 2. `recursive_gap_analysis`
After writing a section draft, this step evaluates the available information:
* It analyzes the draft to determine if there is enough data for a 600-word detailed section.
* If a gap is identified, it generates a query to fetch the missing details, running a secondary web search to fill the information gap.

---

## Tier-Based Outline Planning

The outline structure is managed by `get_template_instructions` in `backend/report_formats.py`. The system configures the layout based on the requested page count, grouping reports into five distinct tiers:

| Tier | Page Range | Number of Sections | Complexity Instructions |
|---|---|---|---|
| **Short** | $\le 6$ | 3 Sections | Focused strictly on the 3 most critical aspects. |
| **Standard** | $7 - 10$ | 4 Sections | Balanced depth (+10% detail, real-world examples). |
| **Deep** | $11 - 15$ | 7 Sections | Deep-Dive analysis, including technical architecture. |
| **Comprehensive** | $16 - 22$ | 10 Sections | Exhaustive coverage, risk analysis, and forecasts. |
| **Monograph** | $\ge 23$ | 15 Sections | Maximum density, historical context, and technical details. |

The template instructions are combined with the topic overview to generate a JSON array of engaging, descriptive section headers.

---

## Matplotlib Graph Generation

To include visual data representations, `generate_chart_from_data` creates charts dynamically:
1. It requests the LLM to extract numeric trends from the synthesized research summary into a structured JSON format containing labels and values.
2. It loads this data into a Pandas DataFrame.
3. It uses Matplotlib (configured with the headless `Agg` backend) to generate a bar chart styled with a modern layout, using hex colors matching the platform's design theme (`#4f46e5`).
4. It saves the resulting PNG image to `static/charts/`.

---

## PDF & Word Document Compiler

The report markdown is compiled into various formats using **Pandoc** and **XeLaTeX**:

* **PDF (`convert_to_pdf`)**:
  Compiles the markdown file using `pypandoc` with the `xelatex` PDF engine. It applies styling variables (e.g., `--pdf-engine-opt=-interaction=nonstopmode` and `-V geometry:margin=1in`) to ensure professional pagination and margin alignment.
* **DOCX (`convert_to_docx`)**:
  Converts the markdown to a Microsoft Word document using Pandoc filters, embedding generated charts as figures.
* **JSON, TXT, MD**:
  Writes the raw text structure directly, packaging it in JSON metadata wrappers where appropriate.

This architecture handles the conversion of research topics into structured, formatted reports. Let's move on to **Chapter 5: Interactive Chat Engine** to review the conversational assistant.
