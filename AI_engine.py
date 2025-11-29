import os
import serpapi
from docx import Document
from docx.shared import Inches
import httpx
from bs4 import BeautifulSoup
import json
import re
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from collections import Counter
import fitz  # PyMuPDF for PDF parsing

# IMPORT THE FORMAT LOGIC
from report_formats import get_template_instructions

AI_MODEL_STRING = "x-ai/grok-4.1-fast:free" 
SEARCH_RESULTS_COUNT = 10
MAX_RESULTS_TO_SCRAPE = 3
WORDS_PER_PAGE = 400

# --- HELPER FUNCTIONS ---

def clean_ai_output(text: str) -> str:
    if not text: return ""
    cleaned = re.sub(r'^```\w*\n?', '', text)
    cleaned = re.sub(r'\n?```$', '', cleaned)
    return cleaned.strip()

def clean_section_output(text: str, section_title: str) -> str:
    if not text: return ""
    lines = text.split('\n')
    first_line = lines[0].strip().lower()
    clean_title = section_title.lower().replace('#', '').strip()
    clean_first = first_line.replace('#', '').strip()
    if clean_title in clean_first or clean_first in clean_title:
        return "\n".join(lines[1:]).strip()
    return text.strip()

# --- CHART GENERATION ---

def generate_chart_from_data(summary: str, topic: str) -> str:
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        chart_dir = "/app/static/charts"
        if not os.path.exists(chart_dir):
            os.makedirs(chart_dir, exist_ok=True)
        
        clean_name = re.sub(r'\W+', '', topic)[:15] 
        filename = f"chart_{clean_name}_{os.urandom(4).hex()}.png"
        filepath = os.path.join(chart_dir, filename)

        system_instr = "You are a Data Analyst. Extract data for a chart."
        prompt = (
            f"Topic: {topic}\n"
            f"Context: {summary[:3000]}\n\n"
            "INSTRUCTIONS:\n"
            "1. Identify any trends, comparisons, or stats.\n"
            "2. If exact data is missing, ESTIMATE values based on context.\n"
            "3. Return ONLY valid JSON: {\"title\": \"...\", \"x_label\": \"...\", \"y_label\": \"...\", \"data\": [{\"label\": \"A\", \"value\": 10}]}"
        )

        chart_data = None
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": AI_MODEL_STRING,
                        "messages": [{"role": "system", "content": system_instr}, {"role": "user", "content": prompt}],
                        "temperature": 0.1
                    }
                )
                content = clean_ai_output(response.json()['choices'][0]['message']['content'])
                match = re.search(r'\{.*\}', content.replace('\n', ' '), re.DOTALL)
                if match:
                    chart_data = json.loads(match.group(0))
        except Exception as e:
            print(f"AI Chart Extraction failed: {e}")

        plt.figure(figsize=(10, 6))
        plt.style.use('ggplot')
        
        if chart_data and 'data' in chart_data and len(chart_data['data']) > 0:
            df = pd.DataFrame(chart_data['data'])
            bars = plt.bar(df['label'], df['value'], color='#4f46e5', alpha=0.8)
            plt.title(chart_data.get('title', 'Analysis'), fontsize=14, pad=20)
            plt.xlabel(chart_data.get('x_label', ''), fontsize=12)
            plt.ylabel(chart_data.get('y_label', ''), fontsize=12)
        else:
            words = re.findall(r'\w+', summary.lower())
            common_words = [w for w in words if len(w) > 4][:8]
            counts = Counter(common_words).most_common(5)
            labels, values = zip(*counts) if counts else (["No Data"], [0])
            plt.bar(labels, values, color='#10b981', alpha=0.6)
            plt.title(f"Key Themes in {topic}", fontsize=14, pad=20)
            plt.xlabel("Keywords", fontsize=12)
            plt.ylabel("Frequency", fontsize=12)

        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(filepath, dpi=100)
        plt.close()
        return filepath
    except Exception as e:
        print(f"Chart Error: {e}")
        return None

# --- SCRAPING (HTML & PDF) ---

def _get_article_text(url: str) -> str:
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        # Increased timeout for PDFs
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            
        if response.status_code != 200: return ""

        # 1. CHECK FOR PDF
        content_type = response.headers.get("Content-Type", "").lower()
        if "application/pdf" in content_type or url.lower().endswith(".pdf"):
            try:
                # Parse PDF from memory bytes
                with fitz.open(stream=response.content, filetype="pdf") as doc:
                    text = ""
                    # Only read first 5 pages to avoid massive token usage
                    for i, page in enumerate(doc):
                        if i > 5: break
                        text += page.get_text()
                print(f"   [PDF Extracted]: {len(text)} chars from {url}")
                return f"--- PDF SOURCE ({url}) ---\n{text[:5000]}\n--- END PDF ---"
            except Exception as e:
                print(f"   [PDF Error]: {e}")
                return ""

        # 2. FALLBACK TO HTML PARSING
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe"]): 
            script.decompose()
            
        content = soup.find('article') or soup.find('main') or soup.find('div', class_=re.compile(r'content|post|article|body'))
        if not content: content = soup
        
        paragraphs = content.find_all(['p', 'h2', 'h3', 'li'])
        text_content = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip().split()) > 6]
        return "\n\n".join(text_content)[:3000]
        
    except Exception as e: 
        print(f"Scrape Error: {e}")
        return ""

def get_search_results(query: str, max_results: int = SEARCH_RESULTS_COUNT) -> str:
    try:
        api_key = os.environ.get("API_KEY") 
        if not api_key: return "Error: SERPAPI_KEY not set."
        
        params = {"q": query, "location": "US", "hl": "en", "gl": "us", "num": max_results, "api_key": api_key, "engine": "google"}
        client = serpapi.Client(api_key=api_key)
        results = client.search(params)
        
        if "error" in results: return f"Error: {results['error']}"
        
        snippets = []
        if "organic_results" in results:
            for i, result in enumerate(results["organic_results"]):
                snippet = result.get("snippet", "")
                url = result.get("link", "")
                title = result.get('title', 'No Title')
                
                full_text = ""
                # Scrape top 3 results (supports PDF now)
                if max_results > 3 and i < MAX_RESULTS_TO_SCRAPE: 
                    print(f"Scraping: {url}...")
                    raw = _get_article_text(url)
                    if raw: full_text = f"\n{raw}\n"
                    
                snippets.append(f"Source: {title}\nURL: {url}\nSummary: {snippet}{full_text}")
                
        return "\n\n".join(snippets) if snippets else "No results."
    except Exception as e: return f"Search Error: {e}"

# --- THE CRITIC LOOP ---

def perform_targeted_search(missing_info: str) -> str:
    print(f"   >>> CRITIC TRIGGERED: Searching for '{missing_info}'...")
    return get_search_results(missing_info, max_results=3)

def critique_and_refine(section_text: str, topic: str) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    critic_prompt = (
        f"Topic: {topic}\nDraft Section:\n{section_text[:3000]}\n\n"
        "Task: Identify ONE specific missing number/fact. Return ONLY the search query. If good, return 'Pass'."
    )
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": AI_MODEL_STRING, "messages": [{"role": "user", "content": critic_prompt}], "temperature": 0.1}
            )
            critique = clean_ai_output(response.json()['choices'][0]['message']['content'])
            
            if "Pass" in critique or len(critique) > 100: return section_text 
            
            new_data = perform_targeted_search(critique)
            if "Error" in new_data or "No results" in new_data: return section_text

            refine_prompt = (
                f"Original Draft:\n{section_text}\n\nNew Data:\n{new_data[:2000]}\n\n"
                "Task: Integrate data into the draft. Maintain Markdown."
            )
            response = client.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": AI_MODEL_STRING, "messages": [{"role": "user", "content": refine_prompt}], "temperature": 0.4}
            )
            return clean_ai_output(response.json()['choices'][0]['message']['content'])
    except Exception as e:
        print(f"Critic Loop Error: {e}")
        return section_text

# --- AI GENERATION ---

def generate_summary(search_content: str, topic: str) -> str:
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        prompt = f"Topic: {topic}\nData:\n{search_content[:12000]}\nTask: Summarize key facts." 
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": AI_MODEL_STRING, "messages": [{"role": "user", "content": prompt}], "temperature": 0.4}
            )
            return response.json()['choices'][0]['message']['content']
    except Exception: return "Summary failed."

def generate_outline(topic: str, summary: str, format_type: str, target_pages: int) -> list:
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        format_data = get_template_instructions(format_type, target_pages)
        prompt = f"Topic: {topic}\nStructure: {format_data['template_text']}\nContext: {summary[:2000]}\nOutput: JSON Array ONLY."
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": AI_MODEL_STRING, "messages": [{"role": "system", "content": "Return JSON array of strings."}, {"role": "user", "content": prompt}], "temperature": 0.3}
            )
            content = response.json()['choices'][0]['message']['content']
        match = re.search(r'\[.*\]', content.replace('\n', ' '), re.DOTALL)
        return json.loads(match.group(0)) if match else ["1. Intro", "2. Analysis", "3. Conclusion"]
    except Exception: return ["1. Intro", "2. Analysis", "3. Conclusion"]

def write_section(section_title: str, topic: str, summary: str, previous_context: str, word_limit: int) -> str:
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        system_instruction = f"Write section '{section_title}'. Academic tone. Use Markdown. No starting header."
        prompt = f"Topic: {topic}\nContext: {summary}\nSection: {section_title}\nLength: {word_limit} words"
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": AI_MODEL_STRING, "messages": [{"role": "system", "content": system_instruction}, {"role": "user", "content": prompt}], "temperature": 0.5}
            )
            draft = clean_ai_output(response.json()['choices'][0]['message']['content'])
            
            if word_limit > 300:
                return critique_and_refine(draft, topic)
            return draft
            
    except Exception as e: return f"(Error: {e})"

# --- MAIN ORCHESTRATOR ---

def run_ai_engine_with_return(query: str, user_format: str, page_count: int = 15, task=None) -> tuple[str, str, str]: 
    def _update_status(message: str):
        print(message) 
        if task: task.update_state(state='PROGRESS', meta={'message': message})

    if not query: return "No query.", "", None

    _update_status("Step 1/6: Global Search (incl. PDFs)...")
    search_content = get_search_results(query)
    
    _update_status("Step 2/6: Synthesizing...")
    summary = generate_summary(search_content, query)
    
    _update_status("Step 3/6: Data Visualization...")
    chart_path = generate_chart_from_data(summary, query)
    
    _update_status(f"Step 4/6: Planning Structure...")
    outline = generate_outline(query, summary, user_format, page_count)
    
    total_words = page_count * WORDS_PER_PAGE 
    words_per_section = max(300, min(int(total_words / max(1, len(outline))), 1500))
    
    full_report = f"# {query.upper()}\n\n"
    for i, section in enumerate(outline):
        _update_status(f"Step 5/6: Drafting & Critiquing {i+1}/{len(outline)}...")
        
        raw_content = write_section(section, query, summary, full_report, words_per_section)
        clean_content = clean_section_output(raw_content, section)
        
        full_report += f"\n\n## {section}\n{clean_content}\n"
    
    _update_status("Step 6/6: Formatting...")
    full_report = clean_ai_output(full_report)
    
    return search_content, full_report, chart_path

# --- CONVERTERS ---
def convert_to_txt(report_content: str, filepath: str) -> str:
    with open(filepath, "w", encoding="utf-8") as f: f.write(report_content)
    return f"Success: TXT file created at {filepath}"

def convert_to_docx(report_content: str, topic: str, filepath: str, chart_path: str = None) -> str:
    doc = Document()
    doc.add_heading(topic, 0)
    if chart_path and os.path.exists(chart_path):
        try:
            doc.add_picture(chart_path, width=Inches(6))
            doc.add_paragraph("Figure 1: Analysis", style='Caption')
        except: pass
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

def convert_to_pdf(report_content: str, topic: str, filepath: str, chart_path: str = None) -> str:
    doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    flowables = []
    flowables.append(Paragraph(topic, styles['Title']))
    flowables.append(Spacer(1, 12))
    if chart_path and os.path.exists(chart_path):
        try:
            img = RLImage(chart_path, width=450, height=250)
            flowables.append(img)
            flowables.append(Spacer(1, 12))
        except: pass
    style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=11, leading=15, spaceAfter=10)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=14, spaceAfter=10, spaceBefore=10)
    for line in report_content.split('\n'):
        clean = line.strip().replace('#', '').replace('*', '&bull;')
        if not clean: continue
        if line.startswith('#'): flowables.append(Paragraph(clean, heading_style))
        else: flowables.append(Paragraph(clean, style))
    doc.build(flowables)
    return f"Success: PDF file created at {filepath}"

def convert_to_json(report_content: str, topic: str, filepath: str) -> str:
    data = {"topic": topic, "content": report_content, "generated_by": "ScholarForge"}
    with open(filepath, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)
    return f"Success: JSON file created at {filepath}"