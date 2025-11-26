import os
import serpapi
from docx import Document
from docx.shared import Pt
import requests
from bs4 import BeautifulSoup
import json
import re
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

AI_MODEL_STRING = "x-ai/grok-4.1-fast:free" # Check your specific model string
SEARCH_RESULTS_COUNT = 10
MAX_RESULTS_TO_SCRAPE = 3
WORDS_PER_PAGE = 500  # THE ANCHOR: 500 words = approx 1 page.

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
            if len(text.split()) > 5:
                text_content.append(text)

        article_text = "\n\n".join(text_content)
        return article_text[:4000] # Limit char count per article
    except Exception as e:
        return f"Error parsing page: {e}"

def get_search_results(query: str) -> str:
    try:
        api_key = os.environ.get("SERPAPI_KEY") 
        if not api_key: return "Error: SERPAPI_KEY environment variable not set."
            
        params = {
            "q": query, "location": "India", "hl": "en", "gl": "us",
            "num": SEARCH_RESULTS_COUNT, "api_key": api_key, "engine": "google"
        }

        client = serpapi.Client(api_key=api_key)
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
                        full_content_text = f"\n\n--- Full Text (Source {i+1}) ---\n{raw_text[:2000]}\n--- End of Full Text ---" 
                    except Exception as e:
                        print(f"Skipping scrape: {e}")

                formatted_snippet = f"[{i+1}] Title: {title}\nSnippet: {snippet_text}\nSource: {source_url}{full_content_text}" 
                snippets.append(formatted_snippet)

        return "\n\n---\n\n".join(snippets) if snippets else "No relevant search results were found."
    except Exception as e:
        return f"Search Error: {e}"

# --- AI GENERATION FUNCTIONS ---

def generate_summary(search_content: str, topic: str) -> str:
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key: return "Error: OPENROUTER_API_KEY not set."

        system_instruction = "You are a Senior Research Analyst. Synthesize the search results into a detailed research briefing."
        
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
                "max_tokens": 2000
            })
        )
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Summarization Error: {e}"

def generate_outline(topic: str, summary: str, user_format: str, target_pages: int) -> list:
    """
    Generates a FLAT outline scaled to the target page count.
    """
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        
        # LOGIC: 10 Pages / 1.5 = 6.6 -> 7 Sections.
        ideal_section_count = max(4, int(target_pages / 1.5))
        
        system_instruction = (
            "You are a Structural Editor. Generate a flat report outline (JSON array). "
            "Do NOT use sub-headers (e.g. 1.1). One level only."
        )
        
        prompt = (
            f"Topic: {topic}\n"
            f"Target Report Length: {target_pages} pages.\n"
            f"Base Format Template:\n{user_format}\n\n"
            "INSTRUCTIONS:\n"
            f"1. Generate exactly {ideal_section_count} main section headers to fit the target length.\n"
            "2. Ignore complex numbering in the template. Use simple headers.\n"
            "3. Return ONLY a JSON list of strings (e.g. [\"1. Introduction\", \"2. Analysis\"])."
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
            return json.loads(match.group(0))
        return ["1. Introduction", "2. Main Analysis", "3. Conclusion"] # Fallback

    except Exception:
        return ["1. Introduction", "2. Main Analysis", "3. Conclusion"]

def write_section(section_title: str, topic: str, summary: str, previous_context: str, word_limit: int) -> str:
    """
    Writes a section with a specific word limit.
    """
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        
        system_instruction = (
            f"You are a Report Writer. Write ONE section of a report. "
            f"Target word count: approximately {word_limit} words. "
            "Be academic and detailed. Use citations [1] from the research."
        )
        
        prompt = (
            f"Report Topic: {topic}\n"
            f"Current Section: {section_title}\n"
            f"Target Words: {word_limit}\n\n"
            f"Research Context:\n{summary}\n\n"
            f"Previous context: ...{previous_context[-300:] if previous_context else 'Start'}"
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
                "max_tokens": int(word_limit * 2.5) # Buffer for tokens
            })
        )
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"\n(Error writing section {section_title}: {e})\n"

def run_ai_engine_with_return(query: str, user_format: str, page_count: int = 15, task=None) -> tuple[str, str] | str: 
    """
    Orchestrates the Chain of Agents with Math Logic.
    """
    # 1. DEFINE UPDATE HELPER
    def _update_status(message: str):
        print(message) 
        if task: task.update_state(state='PROGRESS', meta={'message': message})

    if not query: return "Please provide a search query."

    # 2. SEARCH
    _update_status("Step 1/5: Searching & Scraping...")
    search_content = get_search_results(query)
    if search_content.startswith("Error"): return f"Search failed: {search_content}"

    # 3. SUMMARY
    _update_status("Step 2/5: Synthesizing Research...")
    summary = generate_summary(search_content, query)
    
    # 4. OUTLINE
    _update_status(f"Step 3/5: Planning {page_count}-Page Structure...")
    # Pass page_count to outline generator
    outline = generate_outline(query, summary, user_format, page_count)
    
    # 5. MATH LOGIC (The Fix)
    total_target_words = page_count * WORDS_PER_PAGE 
    # Calculate words per section
    words_per_section = int(total_target_words / max(1, len(outline)))
    
    # Safety Bounds
    if words_per_section < 300: words_per_section = 300
    if words_per_section > 1200: words_per_section = 1200
    
    # 6. WRITE SECTIONS
    full_report = f"# {query.upper()}\n\n"
    total_sections = len(outline)
    
    for i, section in enumerate(outline):
        _update_status(f"Step 4/5: Writing Section {i+1}/{total_sections} (~{words_per_section} words)...")
        
        # Pass word_limit to writer
        section_content = write_section(section, query, summary, full_report, words_per_section)
        
        full_report += f"\n## {section}\n{section_content}\n\n"
    
    _update_status("Step 5/5: Final Polish...")
    return search_content, full_report

# --- CONVERTERS ---

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
        
        style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=14)
        clean_text = report_content.replace('#', '').replace('*', '•')
        para = Paragraph(clean_text.replace('\n', '<br/>'), style)
        flowables.append(para)

        doc.build(flowables)
        return f"Success: PDF file created at {filepath}"
    except Exception as e: 
        return f"Error creating PDF: {e}"