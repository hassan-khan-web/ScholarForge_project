import os
from docx import Document
import httpx
from bs4 import BeautifulSoup
import json
import re
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import pandas as pd
import fitz 

from .report_formats import get_template_instructions
from .logging_config import setup_logging

logger = setup_logging("scholarforge.ai_engine")

SMART_MODEL = "llama-3.3-70b-versatile"
BACKUP_MODEL = "llama-3.1-8b-instant"

SEARCH_RESULTS_COUNT = 10
MAX_RESULTS_TO_SCRAPE = 4
WORDS_PER_PAGE = 450

def clean_ai_output(text: str) -> str:
    if not text: return ""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'^```\w*\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*$', '', text, flags=re.MULTILINE)
    return text.strip()

def clean_section_output(text: str, section_title: str) -> str:
    if not text:
        return ""
    text = clean_ai_output(text)
    lines = text.split('\n')
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return ""
    first_line = lines[0].strip().lower()
    clean_title = section_title.lower().replace('#', '').strip()
    clean_first = first_line.replace('#', '').strip()
    
    if clean_title in clean_first or clean_first in clean_title:
        return "\n".join(lines[1:]).strip()
    return text.strip()

def get_fallback_chain(target_model: str) -> list:
    hf_models = ["zai-org/GLM-5.1", "Qwen/Qwen3-0.6B", "meta-llama/Llama-3.1-8B-Instruct"]
    groq_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    or_models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    
    chain = []
    # 1. Primary target
    chain.append(target_model)
    
    # 2. Add other models in the same family first, then other families
    if target_model in hf_models:
        for m in hf_models:
            if m not in chain:
                chain.append(m)
        for m in groq_models:
            if m not in chain:
                chain.append(m)
        for m in or_models:
            if m not in chain:
                chain.append(m)
    elif target_model in groq_models:
        for m in groq_models:
            if m not in chain:
                chain.append(m)
        for m in hf_models:
            if m not in chain:
                chain.append(m)
        for m in or_models:
            if m not in chain:
                chain.append(m)
    else:
        for m in or_models:
            if m not in chain:
                chain.append(m)
        for m in groq_models:
            if m not in chain:
                chain.append(m)
        for m in hf_models:
            if m not in chain:
                chain.append(m)
                
    return chain

def call_llm(target_model: str, system_prompt: str, user_prompt: str, temp: float = 0.4, attempt: int = 1) -> str:
    fallback_chain = get_fallback_chain(target_model)
    errors = []
    
    full_system_prompt = system_prompt
    if "Output raw Markdown only" not in full_system_prompt:
        full_system_prompt += " Output raw Markdown only. No code blocks."

    for idx, model in enumerate(fallback_chain):
        logger.info(f"LLM Call: Model={model} (Attempt {idx+1}/{len(fallback_chain)})")
        try:
            is_hf = model in ["zai-org/GLM-5.1", "Qwen/Qwen3-0.6B", "meta-llama/Llama-3.1-8B-Instruct"]
            is_groq = model.startswith("llama-") or "openai/gpt-oss" in model
            
            if is_hf:
                token = os.environ.get("HF_TOKEN")
                if not token:
                    raise ValueError("No HF_TOKEN set in environment.")
                token = token.strip('"').strip("'")
                
                api_url = "https://router.huggingface.co/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": full_system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temp,
                    "max_tokens": 4000
                }
            else:
                if is_groq:
                    api_key = os.environ.get("GROQ_API_KEY")
                    if not api_key:
                        raise ValueError("No GROQ_API_KEY set in environment.")
                    api_url = "https://api.groq.com/openai/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                else:
                    api_key = os.environ.get("OPENROUTER_API_KEY")
                    if not api_key:
                        raise ValueError("No OPENROUTER_API_KEY set in environment.")
                    api_url = "https://openrouter.ai/api/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://localhost:5000",
                        "X-Title": "ScholarForge"
                    }
                
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": full_system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temp,
                    "max_tokens": 5000
                }

            timeout = 120.0
            with httpx.Client(timeout=timeout) as client:
                response = client.post(api_url, headers=headers, json=payload)
                if response.status_code != 200:
                    if response.status_code == 429:
                        import time
                        time.sleep(3)
                    raise RuntimeError(f"API Error ({model}, Status {response.status_code}): {response.text}")
                
                content = response.json()['choices'][0]['message']['content']
                return clean_ai_output(content)
                
        except Exception as e:
            err_msg = f"Model {model} failed: {str(e)}"
            logger.error(err_msg)
            errors.append(err_msg)
            import time
            time.sleep(1)
            continue

    logger.critical("All models in the fallback chain failed.")
    error_details = "\n".join([f"- {err}" for err in errors])
    
    truncated_prompt = user_prompt
    if len(truncated_prompt) > 2000:
        truncated_prompt = truncated_prompt[:2000] + "\n\n...[TRUNCATED FOR LENGTH]..."
        
    fallback_text = (
        f"### [Critical Connection Error: Model Generation Failed]\n\n"
        f"The ScholarForge AI engine was unable to generate content for this section because "
        f"all configured models in the fallback chain returned connection errors or timeouts.\n\n"
        f"**Troubleshooting Info & Error Log:**\n"
        f"{error_details}\n\n"
        f"#### Collected Section Context:\n"
        f"Below is the data and search context compiled for this section:\n\n"
        f"{truncated_prompt}"
    )
    return fallback_text



def extract_text_from_files(file_data_list: list) -> str:
    """Feature: Extract text from MULTIPLE uploaded files (PDF, DOCX, TXT)"""
    combined_text = "\n\n--- USER UPLOADED DOCUMENTS ---\n"
    
    try:
        for idx, file_data in enumerate(file_data_list):
            filename = file_data.get('filename', f'Document_{idx+1}')
            content = file_data.get('content')
            doc_text = ""

            try:
                if filename.lower().endswith('.pdf'):
                    with fitz.open(stream=content, filetype="pdf") as doc:
                        for i, page in enumerate(doc):
                            if i > 25:
                                    break
                            doc_text += page.get_text()
                elif filename.lower().endswith('.docx'):
                    from io import BytesIO
                    # Document is already imported from docx at top level
                    doc = Document(BytesIO(content))
                    for para in doc.paragraphs:
                        doc_text += para.text + "\n"
                elif filename.lower().endswith('.txt') or filename.lower().endswith('.md'):
                    doc_text = content.decode('utf-8', errors='ignore')
                
                combined_text += f"\n[Document {idx+1} - {filename}]:\n{doc_text[:15000]}\n"
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}", exc_info=e)
                continue
        
        combined_text += "\n------------------------------\n"
        return combined_text
    except Exception as e:
        logger.error(f"File Extraction Error: {e}", exc_info=e)
        return ""

def _get_article_text(url: str) -> str:
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
        if response.status_code != 200:
            return ""
        
        if "application/pdf" in response.headers.get("Content-Type", "") or url.endswith(".pdf"):
            return "" 
            
        soup = BeautifulSoup(response.text, 'lxml')
        for tag in soup(['script', 'style', 'nav', 'footer', 'aside']):
            tag.decompose()
        return soup.get_text(separator='\n', strip=True)[:5000] # Increased scrape limit
    except Exception:

        return ""

def get_search_results(query: str, max_results: int = SEARCH_RESULTS_COUNT) -> str:
    """Feature: Structured Source Verification with Tavily"""
    query = query.strip()
    if not query:
        return ""
    try:
        api_key = os.environ.get("SERP_KEY")
        if not api_key:
            return "Error: SERP_KEY not set."
        
        logger.info(f"Searching Tavily for: {query}")
        
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "include_answer": False,
            "include_images": False,
            "include_item_list": False,
            "max_results": 5
        }
        
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(url, json=payload)
                
            if response.status_code != 200:
                return f"Tavily Search Error: {response.status_code} - {response.text}"
                
            results = response.json()
            formatted_output = "--- VERIFIED SOURCES ---\n"
            
            if "results" in results:
                for i, result in enumerate(results["results"]):
                    if i >= MAX_RESULTS_TO_SCRAPE:
                        break
                    
                    link = result.get("url", "")
                    title = result.get('title', 'Unknown Title')
                    snippet = result.get("content", "")
                    
                    full_content = ""
                    # Optional: still try to scrape if Tavily's content is too short, 
                    # but Tavily usually gives good context. 
                    # We can retain the _get_article_text for deeper dives if needed,
                    # but for now we'll trust Tavily's snippet/content as primary.
                    
                    formatted_output += f"SOURCE [{i+1}]\nTitle: {title}\nURL: {link}\nSummary: {snippet}{full_content}\n\n"
                    
            return formatted_output
            
        except Exception as http_err:
            return f"Tavily Request Error: {http_err}"
            
    except Exception as e:
        return f"Search Error: {e}"


def recursive_gap_analysis(section_title: str, existing_summary: str, topic: str, model: str = SMART_MODEL) -> str:
    """Feature: Recursive Research. Checks if we need more info."""
    logger.info(f"Analyzing gap for: {section_title}")
    prompt = (
        f"We are writing a report on '{topic}'.\n"
        f"Current Section: '{section_title}'\n"
        f"Available Data Summary: {existing_summary[:3000]}\n\n"
        "DECISION: Do we have specific enough data to write a detailed 600-word section with stats and tables on this specific sub-topic?\n"
        "If YES, output 'PASS'.\n"
        "If NO, output a Google Search Query to find the missing specific info."
    )
    decision = call_llm(model, "You are a Research Director.", prompt, temp=0.1)
    
    if "PASS" in decision or len(decision) > 100:
        return "" 
    
    new_query = decision.strip().replace('"', '')
    if not new_query:
        return ""
    logger.info(f"Recursive search triggered for: {new_query}")
    return get_search_results(new_query, max_results=2)

def assess_search_need(query: str, existing_context: str, model: str = SMART_MODEL) -> str:
    """Feature: Check if we actually need to search the web."""
    logger.debug(f"Assessing search need for: {query}")
    prompt = (
        f"Query: '{query}'\n"
        f"Existing Context Length: {len(existing_context)} chars\n"
        f"Existing Context Preview: {existing_context[:1000]}\n\n"
        "DECISION: To write a high-quality, detailed report on this, do we STRICTLY need external live web search data?\n"
        "Criteria:\n"
        "- If it is a well-known topic (history, science, standard concepts) or purely creative -> NO.\n"
        "- If the provided Context answers it -> NO.\n"
        "- If it requires REAL-TIME news, specific recent data (post-2023), or obscure info -> YES.\n\n"
        "OUTPUT:\n"
        "- If NO (we can skip search): Output 'SKIP_SEARCH'.\n"
        "- If YES (we need search): Output a specific, optimized Google Search Query."
    )
    decision = call_llm(model, "You are a Research Director.", prompt, temp=0.1)
    
    clean_decision = decision.strip().replace('"', '')
    if 'SKIP_SEARCH' in clean_decision:
        return 'SKIP_SEARCH'
    return clean_decision

def generate_summary(search_content: str, topic: str, user_pdf_text: str = "", model: str = SMART_MODEL) -> str:
    context = search_content
    if user_pdf_text:
        context = user_pdf_text + "\n\n" + search_content
        
    return call_llm(
        model,
        "You are a Senior Research Analyst.",
        f"Topic: {topic}\n\nData:\n{context[:35000]}\n\nTask: Synthesize a master summary of key facts, numbers, and sources. Group them by themes.\nIMPORTANT: If the Data seems empty or insufficient, rely on your extensive INTERNAL KNOWLEDGE to generate the summary."
    )

def generate_outline(topic: str, summary: str, format_type: str, target_pages: int, model: str = SMART_MODEL) -> list:
    format_data = get_template_instructions(format_type, target_pages)
    
    target_count = format_data['target_sections']
    
    prompt = (
        f"Topic: {topic}\n"
        f"Tier Target: {target_count} sections exactly.\n"
        f"Logic: {format_data['template_text']}\n"
        f"Context: {summary[:3000]}\n\n"
        "TASK: Generate the JSON outline.\n"
        "RULES:\n"
        "1. Titles MUST be engaging (e.g. 'The Quantum Leap' instead of 'Introduction').\n"
        "2. Return exactly the number of sections requested.\n"
        "Output: A JSON list of strings ONLY. Example: [\"1. The Awakening\", \"2. Market Forces\"]"
    )
    content = call_llm(model, "Return JSON only.", prompt, temp=0.3)
    match = re.search(r'\[.*\]', content.replace('\n', ' '), re.DOTALL)
    
    if match: 
        outline = json.loads(match.group(0))
        return outline[:target_count] if len(outline) > target_count else outline
        
    return ["1. Executive Overview", "2. Core Analysis", "3. Strategic Implications", "4. Conclusion"]

def write_section(section_title: str, topic: str, summary: str, full_report_context: str, word_limit: int, format_type: str = "literature_review", model: str = SMART_MODEL) -> str:
    new_data = recursive_gap_analysis(section_title, summary, topic, model=model)
    
    combined_data = summary
    if new_data:
        combined_data = new_data + "\n\n" + summary 
        
    from .report_formats import FORMAT_TEMPLATES, COMMON_INSTRUCTION
    if format_type in FORMAT_TEMPLATES:
        format_base = FORMAT_TEMPLATES[format_type]
    else:
        format_base = f"[INSTRUCTION: {format_type}]"
        
    format_rules = format_base.replace("{common_ins}", COMMON_INSTRUCTION).replace("{complexity_note}", "").replace("{section_count}", "thematic")
        
    base_prompt = (
        f"Write the section '{section_title}' for the report '{topic}'.\n"
        f"Data Source:\n{combined_data[:20000]}\n\n"
        f"Length Target: {word_limit} words.\n\n"
        f"REPORT FORMAT STYLE AND OBJECTIVE:\n{format_rules}\n\n"
        "FORMATTING RULES (STRICT):\n"
        "1. HEADER: Use the section title as # H1.\n"
        "2. SUB-HEADERS: Use ### H3 for sub-themes. Do NOT use generic names.\n"
        "3. TABLES: You MUST include at least one Markdown table comparing data, pros/cons, or timelines.\n"
        "4. CITATIONS: Use [1], [2] notation corresponding to sources.\n"
        "5. TONE: Professional, dense, and analytical. Avoid fluff.\n"
        "6. CONTENT: If this is 'Standard' or higher, include a 'Real World Application' subsection.\n"
        "7. REFERENCES: Do NOT output a 'References' list at the end of this section. Citations [x] are sufficient."
    )
    
    content = call_llm(model, "You are a Report Writer. Use Markdown Tables and Charts.", base_prompt, temp=0.4)
    return clean_section_output(content, section_title)

def generate_chart_from_data(summary: str, topic: str, model: str = SMART_MODEL) -> str:
    try:
        chart_dir = os.path.join("frontend", "static", "charts")
        if not os.path.exists(chart_dir): os.makedirs(chart_dir, exist_ok=True)
        clean_name = re.sub(r'\W+', '', topic)[:15] 
        filename = f"chart_{clean_name}_{os.urandom(4).hex()}.png"
        filepath = os.path.join(chart_dir, filename)

        prompt = (
            f"Topic: {topic}\nContext: {summary[:3000]}\n"
            "Extract key numeric trends. Return JSON: {\"title\": \"...\", \"x_label\": \"...\", \"y_label\": \"...\", \"data\": [{\"label\": \"A\", \"value\": 10}]}"
        )
        content = call_llm(model, "Return JSON only.", prompt, temp=0.1)
        match = re.search(r'\{.*\}', content.replace('\n', ' '), re.DOTALL)
        if not match: return None
        chart_data = json.loads(match.group(0))
        if not chart_data or 'data' not in chart_data: return None

        # Clean data to ensure values are numeric
        cleaned_data = []
        for item in chart_data['data']:
            val = item.get('value', 0)
            if isinstance(val, str):
                try:
                    numeric_str = re.sub(r'[^\d.-]', '', val)
                    val = float(numeric_str) if numeric_str else 0.0
                except ValueError:
                    val = 0.0
            elif val is None:
                val = 0.0
            cleaned_data.append({
                'label': str(item.get('label', '')),
                'value': float(val)
            })

        df = pd.DataFrame(cleaned_data)
        fig, ax = plt.subplots(figsize=(10, 6))
        plt.style.use('ggplot')
        ax.bar(df['label'], df['value'], color='#4f46e5', alpha=0.8)
        ax.set_title(chart_data.get('title', 'Analysis'), fontsize=14, pad=20)
        ax.set_xlabel(chart_data.get('x_label', ''), fontsize=12)
        ax.set_ylabel(chart_data.get('y_label', ''), fontsize=12)
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        fig.tight_layout()
        fig.savefig(filepath, dpi=100)
        plt.close(fig)
        return os.path.join("static", "charts", filename)
    except Exception:
        return None

def format_bibliography(search_content: str) -> str:
    if not search_content or "--- VERIFIED SOURCES ---" not in search_content:
        return ""
    
    import re
    pattern = r"SOURCE \[(\d+)\]\s*\nTitle:\s*(.*?)\nURL:\s*(.*?)\nSummary:\s*(.*?)(?=\n+SOURCE \[\d+\]|\Z)"
    matches = re.findall(pattern, search_content, re.DOTALL)
    
    if not matches:
        return search_content.replace("--- VERIFIED SOURCES ---", "").strip()
        
    bib = ""
    for num, title, url, summary in matches:
        title = title.strip()
        url = url.strip()
        summary = summary.strip()
        if not title or title.lower() == 'unknown title':
            try:
                from urllib.parse import urlparse
                title = urlparse(url).netloc or url
            except:
                title = "Verified Source"
        bib += f"[{num}] **{title}** — [Link to Source]({url})\n\n"
    return bib.strip()

from . import council

def run_ai_engine_with_return(query: str, user_format: str, page_count: int = 15, file_data_list: list = None, task=None, use_council: bool = False, model: str = SMART_MODEL) -> tuple[str, str, str]: 
    def _update_status(message: str):
        logger.info(message) 
        if task: task.update_state(state='PROGRESS', meta={'message': message})

    _update_status("Step 1/7: Processing Inputs...")
    
    user_pdf_text = ""
    if file_data_list:
        user_pdf_text = extract_text_from_files(file_data_list)
        _update_status(f"    > Analyzed {len(file_data_list)} uploaded documents.")

    _update_status("Step 2/7: Checking Information Needs...")
    
    search_decision = assess_search_need(query, user_pdf_text, model=model)
    
    search_content = ""
    if search_decision == 'SKIP_SEARCH':
        _update_status("    > Sufficient internal/provided info. Skipping Web Search.")
        search_content = "[Internal Knowledge & User Documents Mode Active - Web Search Skipped]"
    else:
        _update_status(f"    > Web Search Required: {search_decision}")
        search_content = get_search_results(search_decision)
    
    _update_status("Step 3/7: Synthesizing Data...")
    summary = generate_summary(search_content, query, user_pdf_text, model=model)
    
    _update_status("Step 4/7: Generating Visuals...")
    chart_path = generate_chart_from_data(summary, query, model=model)
    
    _update_status("Step 5/7: Planning Structure...")
    outline = generate_outline(query, summary, user_format, page_count, model=model)

    total_words = page_count * WORDS_PER_PAGE 
    words_per_section = max(400, int(total_words / max(1, len(outline))))
    
    full_report = f"# {query.upper()}\n\n"
    for i, section in enumerate(outline):
        _update_status(f"Step 6/7: Writing Section {i+1}/{len(outline)}: {section}...")
        
        if use_council:
            # COUNCIL MODE: Use the multi-agent recursive loop
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            section_content = loop.run_until_complete(
                council.run_council(section, query, summary, _update_status)
            )
        else:
            # STANDARD MODE
            section_content = write_section(section, query, summary, full_report, words_per_section, user_format, model=model)
            
        full_report += f"\n\n## {section}\n{section_content}\n"
    
    # Append Consolidated References
    full_report += "\n\n# References\n"
    # Format Tavily bibliography
    clean_refs = format_bibliography(search_content)
    full_report += clean_refs

    _update_status("Step 7/7: Finalizing...")
    full_report = clean_ai_output(full_report)
    
    return search_content + "\n" + user_pdf_text, full_report, chart_path

def convert_to_txt(content, path):
    with open(path, "w", encoding="utf-8") as f: f.write(content)
    return "Success"
def convert_to_md(content, path):
    with open(path, "w", encoding="utf-8") as f: f.write(content)
    return "Success"
def convert_to_json(content, topic, path):
    data = {"topic": topic, "content": content, "generated_by": "ScholarForge"}
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)
    return "Success"
import pypandoc

def _resolve_chart_path(chart_path: str) -> str:
    if not chart_path:
        return None
    if chart_path.startswith("static/"):
        disk_path = os.path.join("frontend", chart_path)
        if os.path.exists(disk_path):
            return disk_path
    if os.path.exists(chart_path):
        return chart_path
    return None

def _prepare_markdown(content, topic, chart_path=None):
    md = f"# {topic}\n\n"
    resolved = _resolve_chart_path(chart_path)
    if resolved:
        md += f"![Figure 1: Analysis]({resolved})\n\n"
    md += content
    return md

def convert_to_docx(content, topic, path, chart_path=None):
    md = _prepare_markdown(content, topic, chart_path)
    try:
        pypandoc.convert_text(md, 'docx', format='markdown-raw_tex-raw_html', outputfile=path)
        return "Success"
    except Exception as e:
        logger.error(f"Error converting to DOCX: {e}", exc_info=e)
        return str(e)

def convert_to_pdf(content, topic, path, chart_path=None):
    md = _prepare_markdown(content, topic, chart_path)
    try:
        # Inject professional fancy headers & footers into XeLaTeX via Pandoc variables
        header_tex = (
            "\\usepackage{fancyhdr} "
            "\\pagestyle{fancy} "
            "\\fancyhead[L]{ScholarForge Research Workspace} "
            "\\fancyhead[R]{" + topic.replace("_", " ").title() + "} "
            "\\fancyfoot[C]{\\thepage} "
            "\\renewcommand{\\headrulewidth}{0.4pt} "
            "\\renewcommand{\\footrulewidth}{0.4pt}"
        )
        
        pypandoc.convert_text(md, 'pdf', format='markdown-raw_tex-raw_html', outputfile=path, extra_args=[
            '--pdf-engine=xelatex', 
            '-V', 'geometry:margin=1in',
            '-V', f'header-includes={header_tex}',
            '--pdf-engine-opt=-interaction=nonstopmode'
        ])
        return "Success"
    except Exception as e:
        logger.warning(f"LaTeX Warning: {e}")
        # XeLaTeX returns non-zero exit codes for minor syntax errors, but often still successfully generates the PDF file.
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            return "Success"
        return str(e)