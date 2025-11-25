import os
import serpapi
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import requests
from bs4 import BeautifulSoup
import json
import markdown
import re
# Use lxml_html to avoid namespace collision
from lxml import html as lxml_html 
import html as html_parser
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# NEW IMPORT FOR SPEED
import concurrent.futures 

AI_MODEL_STRING = "x-ai/grok-4.1-fast:free"
SEARCH_RESULTS_COUNT = 10
MAX_RESULTS_TO_SCRAPE = 3
MAX_PARALLEL_WORKERS = 4 # Adjust based on API limits. 4-5 is usually safe.

# --- SCRAPING & SEARCHING ---

def _get_article_text(url: str) -> str:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return f"Failed to retrieve content (Status code: {response.status_code})"

        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.decompose()

        content = soup.find('article')
        if not content: content = soup.find('main')
        if not content: content = soup

        paragraphs = content.find_all(['p', 'h1', 'h2', 'h3', 'li'])
        text_content = []
        
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text.split()) > 5 or (len(text) > 20 and text[-1] in '.!?'):
                text_content.append(text)

        article_text = "\n\n".join(text_content)
        if not article_text or len(article_text) < 100:
            return "No substantial content found on this page."
            
        return article_text
    except Exception as e:
        return f"Error parsing page: {e}"

def get_search_results(query: str) -> str:
    try:
        api_key = os.environ.get("API_KEY") 
        if not api_key: return "Error: API_KEY environment variable not set."
            
        params = {
            "q": query, "location": "India", "hl": "en", "gl": "us",
            "num": SEARCH_RESULTS_COUNT, "api_key": api_key, "engine": "google"
        }

        client = serpapi.Client()
        results = client.search(params)
        
        if "error" in results: return f"Error from SerpApi: {results['error']}"

        snippets = []
        if "organic_results" in results:
            for i, result in enumerate(results["organic_results"]):
                snippet_text = result.get("snippet", "No snippet available.")
                source_url = result.get("link", "No URL available.")
                title = result.get('title', 'No Title')

                full_content_text = ""
                if i < MAX_RESULTS_TO_SCRAPE:
                    try:
                        print(f"Fetching full text from: {source_url}...")
                        raw_text = _get_article_text(source_url)
                        full_content_text = f"\n\n--- Full Text (Source {i+1}) ---\n{raw_text[:3000]}\n--- End of Full Text ---" 
                    except Exception as e:
                        print(f"Skipping scrape: {e}")

                formatted_snippet = f"[{i+1}] Title: {title}\nSnippet: {snippet_text}\nSource: {source_url}{full_content_text}" 
                snippets.append(formatted_snippet)

        return "\n\n---\n\n".join(snippets) if snippets else "No relevant search results were found."
    except Exception as e:
        return f"Search Error: {e}"

# --- AI GENERATION FUNCTIONS (PARALLELIZED) ---

def generate_summary(search_content: str, topic: str) -> str:
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key: return "Error: OPENROUTER_API_KEY not set."

        system_instruction = (
            "You are a Senior Research Analyst. Synthesize the provided search results into a detailed research briefing. "
            "Focus on extracting facts, statistics, conflicting arguments, and key dates. "
            "Retain citation numbers [1], [2]."
        )
        
        prompt = f"Topic: {topic}\n\nRaw Data:\n{search_content[:15000]}" 

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps({
                "model": AI_MODEL_STRING,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.4,
                "max_tokens": 3000
            })
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Summarization Error: {e}"

def generate_outline(topic: str, summary: str, user_format: str) -> list:
    
    # --- HELPER: FALLBACK PARSER ---
    def extract_headers_from_format(fmt_string):
        headers = []
        for line in fmt_string.split('\n'):
            line = line.strip()
            if line.startswith('# ') or line.startswith('## '):
                clean_line = line.replace('#', '').strip()
                if "[INSTRUCTION" not in clean_line:
                    headers.append(clean_line)
        return headers

    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        
        system_instruction = (
            "You are a Structural Editor. Your task is to take a 'Report Skeleton' "
            "and fill in the bracketed placeholders [ ] with specific topics based on the research. "
            "You must Output ONLY a raw JSON array of strings representing the section headers."
        )
        
        prompt = (
            f"Topic: {topic}\n\n"
            f"REQUIRED REPORT SKELETON:\n{user_format}\n\n"
            "Instructions:\n"
            "1. Read the Skeleton above.\n"
            "2. Keep the numbering exactly as is.\n"
            "3. Replace generic placeholders like '[Theme A]' with actual themes.\n"
            "4. Return a JSON list of strings."
        )

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps({
                "model": AI_MODEL_STRING,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            })
        )
        content = response.json()['choices'][0]['message']['content']
        
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            json_str = match.group(0)
            sections = json.loads(json_str)
            if isinstance(sections, list) and len(sections) > 0:
                return sections
        
        return extract_headers_from_format(user_format)

    except Exception as e:
        return extract_headers_from_format(user_format)

# --- UPDATED WRITER (Removed 'previous_context' for parallelization) ---
def write_section(section_title: str, topic: str, summary: str) -> dict:
    """
    Writes a single section. Returns dict with title and content to preserve order.
    """
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        
        system_instruction = (
            "You are a Report Writer. Write ONE section of a larger report. "
            "Be extremely detailed. Write at least 800 words. "
            "Use academic language. Use citations [1] from the summary. "
        )
        
        prompt = (
            f"Report Topic: {topic}\n"
            f"Current Section to Write: {section_title}\n\n"
            f"Research Context:\n{summary}\n\n"
            "Instruction: Write strictly for this section. Do not write an Introduction or Conclusion unless the title asks for it."
        )

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps({
                "model": AI_MODEL_STRING,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.4,
                "max_tokens": 2000 
            })
        )
        content = response.json()['choices'][0]['message']['content']
        return {"title": section_title, "content": content}
    except Exception as e:
        return {"title": section_title, "content": f"(Error writing section: {e})"}

def run_ai_engine_with_return(query: str, user_format: str, page_count: int = 15, task=None) -> tuple[str, str] | str: 
    """
    Orchestrates the Parallel Chain of Agents.
    """
    def _update_status(message: str):
        print(message) 
        if task: task.update_state(state='PROGRESS', meta={'message': message})

    if not query: return "Please provide a search query."

    _update_status("Step 1/5: Searching & Scraping...")
    search_content = get_search_results(query)
    if search_content.startswith("Error"): return f"Search failed: {search_content}"

    _update_status("Step 2/5: Synthesizing Research...")
    summary = generate_summary(search_content, query)
    
    _update_status("Step 3/5: Planning Report Structure...")
    outline = generate_outline(query, summary, user_format)
    
    # --- PARALLEL EXECUTION START ---
    full_report = f"# {query.upper()}\n\n"
    total_sections = len(outline)
    
    _update_status(f"Step 4/5: Writing {total_sections} sections in parallel...")
    
    results = [None] * total_sections # Placeholders
    
    # We use a ThreadPool to make multiple API calls at once
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
        # Submit all tasks
        future_to_index = {
            executor.submit(write_section, section, query, summary): i 
            for i, section in enumerate(outline)
        }
        
        completed_count = 0
        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            try:
                data = future.result()
                results[index] = data # Store in correct order
                completed_count += 1
                _update_status(f"Step 4/5: Completed {completed_count}/{total_sections} sections...")
            except Exception as e:
                results[index] = {"title": outline[index], "content": f"Error: {e}"}

    # Stitch them together in order
    for res in results:
        if res:
            full_report += f"\n## {res['title']}\n{res['content']}\n\n"
    
    # --- PARALLEL EXECUTION END ---
    
    _update_status("Step 5/5: Final Polish...")
    return search_content, full_report

# --- CONVERTERS (Standard) ---

def convert_to_txt(report_content: str, filepath: str) -> str:
    try:
        with open(filepath, "w", encoding="utf-8") as f: f.write(report_content)
        return f"Success: TXT file created at {filepath}"
    except Exception as e: return f"Error creating TXT: {e}"

def convert_to_docx(report_content: str, topic: str, filepath: str) -> str:
    try:
        doc = Document()
        doc.add_heading(topic, 0)
        lines = report_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line: continue
            if line.startswith('## '): doc.add_heading(line.replace('## ', ''), level=2)
            elif line.startswith('# '): doc.add_heading(line.replace('# ', ''), level=1)
            elif line.startswith('### '): doc.add_heading(line.replace('### ', ''), level=3)
            elif line.startswith('* ') or line.startswith('- '): doc.add_paragraph(line[2:], style='List Bullet')
            else: doc.add_paragraph(line)
        doc.save(filepath)
        return f"Success: DOCX file created at {filepath}"
    except Exception as e: return f"Error creating DOCX: {e}"

def convert_to_pdf(report_content: str, topic: str, filepath: str) -> str:
    try:
        doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        styles = getSampleStyleSheet()
        flowables = []
        flowables.append(Paragraph(topic, styles['Title']))
        flowables.append(Spacer(1, 12))
        
        # Robust PDF generation (Preformatted to avoid crashes)
        style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=14)
        clean_text = report_content.replace('#', '').replace('*', '•')
        para = Paragraph(clean_text.replace('\n', '<br/>'), style)
        flowables.append(para)

        doc.build(flowables)
        return f"Success: PDF file created at {filepath}"
    except Exception as e: 
        print(f"PDF Error: {e}")
        return f"Error creating PDF: {e}"import os
import serpapi
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import requests
from bs4 import BeautifulSoup
import json
import markdown
import re
# Use lxml_html to avoid namespace collision
from lxml import html as lxml_html 
import html as html_parser
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# NEW IMPORT FOR SPEED
import concurrent.futures 

AI_MODEL_STRING = "x-ai/grok-4.1-fast:free"
SEARCH_RESULTS_COUNT = 10
MAX_RESULTS_TO_SCRAPE = 3
MAX_PARALLEL_WORKERS = 4 # Adjust based on API limits. 4-5 is usually safe.

# --- SCRAPING & SEARCHING ---

def _get_article_text(url: str) -> str:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return f"Failed to retrieve content (Status code: {response.status_code})"

        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.decompose()

        content = soup.find('article')
        if not content: content = soup.find('main')
        if not content: content = soup

        paragraphs = content.find_all(['p', 'h1', 'h2', 'h3', 'li'])
        text_content = []
        
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text.split()) > 5 or (len(text) > 20 and text[-1] in '.!?'):
                text_content.append(text)

        article_text = "\n\n".join(text_content)
        if not article_text or len(article_text) < 100:
            return "No substantial content found on this page."
            
        return article_text
    except Exception as e:
        return f"Error parsing page: {e}"

def get_search_results(query: str) -> str:
    try:
        api_key = os.environ.get("API_KEY") 
        if not api_key: return "Error: API_KEY environment variable not set."
            
        params = {
            "q": query, "location": "India", "hl": "en", "gl": "us",
            "num": SEARCH_RESULTS_COUNT, "api_key": api_key, "engine": "google"
        }

        client = serpapi.Client()
        results = client.search(params)
        
        if "error" in results: return f"Error from SerpApi: {results['error']}"

        snippets = []
        if "organic_results" in results:
            for i, result in enumerate(results["organic_results"]):
                snippet_text = result.get("snippet", "No snippet available.")
                source_url = result.get("link", "No URL available.")
                title = result.get('title', 'No Title')

                full_content_text = ""
                if i < MAX_RESULTS_TO_SCRAPE:
                    try:
                        print(f"Fetching full text from: {source_url}...")
                        raw_text = _get_article_text(source_url)
                        full_content_text = f"\n\n--- Full Text (Source {i+1}) ---\n{raw_text[:3000]}\n--- End of Full Text ---" 
                    except Exception as e:
                        print(f"Skipping scrape: {e}")

                formatted_snippet = f"[{i+1}] Title: {title}\nSnippet: {snippet_text}\nSource: {source_url}{full_content_text}" 
                snippets.append(formatted_snippet)

        return "\n\n---\n\n".join(snippets) if snippets else "No relevant search results were found."
    except Exception as e:
        return f"Search Error: {e}"

# --- AI GENERATION FUNCTIONS (PARALLELIZED) ---

def generate_summary(search_content: str, topic: str) -> str:
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key: return "Error: OPENROUTER_API_KEY not set."

        system_instruction = (
            "You are a Senior Research Analyst. Synthesize the provided search results into a detailed research briefing. "
            "Focus on extracting facts, statistics, conflicting arguments, and key dates. "
            "Retain citation numbers [1], [2]."
        )
        
        prompt = f"Topic: {topic}\n\nRaw Data:\n{search_content[:15000]}" 

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps({
                "model": AI_MODEL_STRING,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.4,
                "max_tokens": 3000
            })
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Summarization Error: {e}"

def generate_outline(topic: str, summary: str, user_format: str) -> list:
    
    # --- HELPER: FALLBACK PARSER ---
    def extract_headers_from_format(fmt_string):
        headers = []
        for line in fmt_string.split('\n'):
            line = line.strip()
            if line.startswith('# ') or line.startswith('## '):
                clean_line = line.replace('#', '').strip()
                if "[INSTRUCTION" not in clean_line:
                    headers.append(clean_line)
        return headers

    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        
        system_instruction = (
            "You are a Structural Editor. Your task is to take a 'Report Skeleton' "
            "and fill in the bracketed placeholders [ ] with specific topics based on the research. "
            "You must Output ONLY a raw JSON array of strings representing the section headers."
        )
        
        prompt = (
            f"Topic: {topic}\n\n"
            f"REQUIRED REPORT SKELETON:\n{user_format}\n\n"
            "Instructions:\n"
            "1. Read the Skeleton above.\n"
            "2. Keep the numbering exactly as is.\n"
            "3. Replace generic placeholders like '[Theme A]' with actual themes.\n"
            "4. Return a JSON list of strings."
        )

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps({
                "model": AI_MODEL_STRING,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            })
        )
        content = response.json()['choices'][0]['message']['content']
        
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            json_str = match.group(0)
            sections = json.loads(json_str)
            if isinstance(sections, list) and len(sections) > 0:
                return sections
        
        return extract_headers_from_format(user_format)

    except Exception as e:
        return extract_headers_from_format(user_format)

# --- UPDATED WRITER (Removed 'previous_context' for parallelization) ---
def write_section(section_title: str, topic: str, summary: str) -> dict:
    """
    Writes a single section. Returns dict with title and content to preserve order.
    """
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        
        system_instruction = (
            "You are a Report Writer. Write ONE section of a larger report. "
            "Be extremely detailed. Write at least 800 words. "
            "Use academic language. Use citations [1] from the summary. "
        )
        
        prompt = (
            f"Report Topic: {topic}\n"
            f"Current Section to Write: {section_title}\n\n"
            f"Research Context:\n{summary}\n\n"
            "Instruction: Write strictly for this section. Do not write an Introduction or Conclusion unless the title asks for it."
        )

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps({
                "model": AI_MODEL_STRING,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.4,
                "max_tokens": 2000 
            })
        )
        content = response.json()['choices'][0]['message']['content']
        return {"title": section_title, "content": content}
    except Exception as e:
        return {"title": section_title, "content": f"(Error writing section: {e})"}

def run_ai_engine_with_return(query: str, user_format: str, page_count: int = 15, task=None) -> tuple[str, str] | str: 
    """
    Orchestrates the Parallel Chain of Agents.
    """
    def _update_status(message: str):
        print(message) 
        if task: task.update_state(state='PROGRESS', meta={'message': message})

    if not query: return "Please provide a search query."

    _update_status("Step 1/5: Searching & Scraping...")
    search_content = get_search_results(query)
    if search_content.startswith("Error"): return f"Search failed: {search_content}"

    _update_status("Step 2/5: Synthesizing Research...")
    summary = generate_summary(search_content, query)
    
    _update_status("Step 3/5: Planning Report Structure...")
    outline = generate_outline(query, summary, user_format)
    
    # --- PARALLEL EXECUTION START ---
    full_report = f"# {query.upper()}\n\n"
    total_sections = len(outline)
    
    _update_status(f"Step 4/5: Writing {total_sections} sections in parallel...")
    
    results = [None] * total_sections # Placeholders
    
    # We use a ThreadPool to make multiple API calls at once
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
        # Submit all tasks
        future_to_index = {
            executor.submit(write_section, section, query, summary): i 
            for i, section in enumerate(outline)
        }
        
        completed_count = 0
        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            try:
                data = future.result()
                results[index] = data # Store in correct order
                completed_count += 1
                _update_status(f"Step 4/5: Completed {completed_count}/{total_sections} sections...")
            except Exception as e:
                results[index] = {"title": outline[index], "content": f"Error: {e}"}

    # Stitch them together in order
    for res in results:
        if res:
            full_report += f"\n## {res['title']}\n{res['content']}\n\n"
    
    # --- PARALLEL EXECUTION END ---
    
    _update_status("Step 5/5: Final Polish...")
    return search_content, full_report

# --- CONVERTERS (Standard) ---

def convert_to_txt(report_content: str, filepath: str) -> str:
    try:
        with open(filepath, "w", encoding="utf-8") as f: f.write(report_content)
        return f"Success: TXT file created at {filepath}"
    except Exception as e: return f"Error creating TXT: {e}"

def convert_to_docx(report_content: str, topic: str, filepath: str) -> str:
    try:
        doc = Document()
        doc.add_heading(topic, 0)
        lines = report_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line: continue
            if line.startswith('## '): doc.add_heading(line.replace('## ', ''), level=2)
            elif line.startswith('# '): doc.add_heading(line.replace('# ', ''), level=1)
            elif line.startswith('### '): doc.add_heading(line.replace('### ', ''), level=3)
            elif line.startswith('* ') or line.startswith('- '): doc.add_paragraph(line[2:], style='List Bullet')
            else: doc.add_paragraph(line)
        doc.save(filepath)
        return f"Success: DOCX file created at {filepath}"
    except Exception as e: return f"Error creating DOCX: {e}"

def convert_to_pdf(report_content: str, topic: str, filepath: str) -> str:
    try:
        doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        styles = getSampleStyleSheet()
        flowables = []
        flowables.append(Paragraph(topic, styles['Title']))
        flowables.append(Spacer(1, 12))
        
        # Robust PDF generation (Preformatted to avoid crashes)
        style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=14)
        clean_text = report_content.replace('#', '').replace('*', '•')
        para = Paragraph(clean_text.replace('\n', '<br/>'), style)
        flowables.append(para)

        doc.build(flowables)
        return f"Success: PDF file created at {filepath}"
    except Exception as e: 
        print(f"PDF Error: {e}")
        return f"Error creating PDF: {e}"