import os
import serpapi
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import requests
from bs4 import BeautifulSoup
import json
import markdown
from lxml import html
import html as html_parser
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

AI_MODEL_STRING = "x-ai/grok-4.1-fast:free"
SEARCH_RESULTS_COUNT = 10
MAX_RESULTS_TO_SCRAPE = 3

def _get_article_text(url: str) -> str:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return f"Failed to retrieve content (Status code: {response.status_code})"

        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        article_text = "\n".join([p.get_text() for p in paragraphs])

        if not article_text:
            return "No paragraph text found on this page."
            
        return article_text
    except requests.exceptions.RequestException as e:
        return f"Error during web request: {e}"
    except Exception as e:
        return f"Error parsing page: {e}"

def get_search_results(query: str) -> str:
    try:
        api_key = os.environ.get("API_KEY") 
        if not api_key:
            return "Error: API_KEY environment variable not set."
            
        params = {
            "q": query, "location": "India", "hl": "en", "gl": "us",
            "num": SEARCH_RESULTS_COUNT, "api_key": api_key, "engine": "google"
        }

        client = serpapi.Client()
        results = client.search(params)
        
        if "error" in results:
            return f"Error from SerpApi: {results['error']}"

        snippets = []
        if "organic_results" in results:
            for i, result in enumerate(results["organic_results"]):
                snippet_text = result.get("snippet", "No snippet available.")
                source_url = result.get("link", "No URL available.")
                title = result.get('title', 'No Title')

                full_content_text = ""
                if i < MAX_RESULTS_TO_SCRAPE:
                    print(f"Fetching full text from: {source_url}...")
                    full_content_text = _get_article_text(source_url)
                    full_content_text = f"\n\n--- Full Text (Source {i+1}) ---\n{full_content_text}\n--- End of Full Text ---"

                formatted_snippet = (
                    f"[{i+1}] Title: {title}\nSnippet: {snippet_text}\nSource: {source_url}{full_content_text}" 
                )
                snippets.append(formatted_snippet)

        return "\n\n---\n\n".join(snippets) if snippets else "No relevant search results were found."

    except Exception as e:
        return f"An unexpected error occurred during search: {e}"

def generate_summary(search_content: str, topic: str, page_count: int) -> str:
    """
    Generates summary. Accepts 'page_count' to instruct AI on depth.
    """
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return "Error: OPENROUTER_API_KEY environment variable not set."

        system_instruction = (
            '''
            You are a meticulous, critical research analyst. Your task is to perform a deep,
            structured analysis of the provided search results.
            
            IMPORTANT: This is NOT a request for a brief summary. You are to create a
            HIGHLY DETAILED, MULTI-PAGE SYNTHESIS of all the provided text.
            Your goal is to extract every key theme, argument, data point, and conflict.
            
            For each major theme you identify, you MUST provide a deep, multi-paragraph
            explanation, citing the sources.
            '''
            f"This output will be the ONLY source material for a full {page_count}-page report, "
            "so you MUST be exhaustive and detailed. Do not skip details.\n"
            f"Your analysis is for the topic: '{topic}'. Use citation numbers [1], [2], etc."
        )

        prompt = f"Search Results:\n{search_content}"

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps({
                "model": AI_MODEL_STRING,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.4
            })
        )
        response.raise_for_status() 
        result = response.json()
        return result['choices'][0]['message']['content'] or "No summary generated."

    except Exception as e:
        return f"Summarization Error: {e}"

def generate_report(summary: str, topic: str, user_format: str, page_count: int) -> str:
    """
    Generates report. Accepts 'page_count' to instruct AI on length.
    """
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return "Error: OPENROUTER_API_KEY environment variable not set."

        system_instruction = (
            "You are a world-class research analyst and professional report writer. "
            f"Your task is to generate a comprehensive, {page_count}-page report on the topic: '{topic}'.\n\n"
            
            "**CRITICAL CONTENT REQUIREMENT:**\n"
            "You MUST ensure **even content distribution**. The last sections of the report MUST be as detailed as the first.\n"
            "Every single sub-section (e.g., 2.1, 2.1.1) **MUST** contain a minimum of **5 to 6 full lines of text**.\n"
            f"To achieve the {page_count}-page requirement, you must Elaborate, Explain, and Provide Examples for every point.\n\n"
            
            "You MUST follow this user-provided structure EXACTLY:\n"
            f"USER-PROVIDED STRUCTURE:\n{user_format}"
        )

        prompt = (
            "Here is the synthesized summary of my research findings. "
            f"Generate the full {page_count}-page report following the structure provided.\n\n"
            f"SUMMARY:\n{summary}"
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
            })
        )
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content'] or "No report generated."

    except Exception as e:
        return f"Report Generation Error: {e}"

def run_ai_engine_with_return(query: str, user_format: str, page_count: int = 15, task=None) -> tuple[str, str] | str: 
    """
    Runs the full report generation pipeline.
    """
    def _update_status(message: str):
        print(message) 
        if task:
            task.update_state(state='PROGRESS', meta={'message': message})

    if not query: return "Please provide a search query."
    if not user_format: return "Error: No report format provided."

    _update_status("Step 1/4: Fetching search results...")
    search_content = get_search_results(query)
    if search_content.startswith(("Error:", "No relevant")):
        return f"Failed to run search pipeline: {search_content}"

    _update_status(f"Step 2/4: Generating summary for {page_count} pages...")
    summary = generate_summary(search_content, query, page_count)
    if summary.startswith(("Error:", "Summarization Error")):
        return f"Failed to summarize: {summary}"

    _update_status(f"Step 3/4: Writing full {page_count}-page report...")
    report_content = generate_report(summary, query, user_format, page_count)
    
    if report_content.startswith(("Error:", "Report Generation Error")):
        return f"Failed to generate report: {report_content}"
        
    _update_status("Step 4/4: Pipeline complete.")
    return search_content, report_content

# --- CONVERTERS (Unchanged) ---

def convert_to_txt(report_content: str, filepath: str) -> str:
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_content)
        return f"Success: TXT file created at {filepath}"
    except Exception as e:
        return f"Error creating TXT file: {e}"

def add_markdown_to_doc(doc, md_text):
    html_content = markdown.markdown(md_text)
    tree = html.fromstring(f"<html><body>{html_content}</body></html>")
    for el in tree.xpath('//body/*'):
        if el.tag == 'h1':
            p = doc.add_paragraph(el.text_content().strip(), style='Heading 1')
            p.runs[0].font.size = Pt(20)
            p.runs[0].font.bold = True
        elif el.tag == 'h2':
            p = doc.add_paragraph(el.text_content().strip(), style='Heading 2')
            p.runs[0].font.size = Pt(16)
            p.runs[0].font.bold = True
        elif el.tag == 'h3':
            p = doc.add_paragraph(el.text_content().strip(), style='Heading 3')
            p.runs[0].font.size = Pt(14)
            p.runs[0].font.bold = True
        elif el.tag in ['p', 'ul', 'ol', 'li']:
            is_list = el.tag in ['ul', 'ol', 'li']
            if el.tag == 'p' and not el.text and not len(el):
                doc.add_paragraph() 
                continue
            style = 'List Bullet' if is_list else 'Normal'
            p = doc.add_paragraph(style=style)
            if el.text: p.add_run(el.text)
            for child in el:
                text = child.text_content() or '' 
                run = None
                if child.tag in ['strong', 'b']:
                    run = p.add_run(text)
                    run.font.bold = True
                elif child.tag in ['em', 'i']:
                    run = p.add_run(text)
                    run.font.italic = True
                else:
                    run = p.add_run(text)
                if child.tail: p.add_run(child.tail)
        else:
            p = doc.add_paragraph(el.text_content().strip())

def convert_to_docx(report_content: str, topic: str, filepath: str) -> str:
    try:
        doc = Document()
        styles = doc.styles
        styles['Heading 1'].font.name = 'Inter'
        styles['Heading 2'].font.name = 'Inter'
        styles['Heading 3'].font.name = 'Inter'
        styles['Normal'].font.name = 'Inter'
        
        title = doc.add_heading(topic, level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title.runs[0].font.size = Pt(24)
        title.runs[0].font.bold = True
        doc.add_paragraph() 
        add_markdown_to_doc(doc, report_content)
        doc.save(filepath)
        return f"Success: DOCX file created at {filepath}"
    except Exception as e:
        return f"Error creating DOCX file: {e}"

def _get_inner_html_for_reportlab(element):
    inner_content_list = []
    if element.text: inner_content_list.append(html_parser.escape(element.text))
    for child in element:
        inner_content_list.append(html.tostring(child, encoding='unicode'))
        if child.tail: inner_content_list.append(html_parser.escape(child.tail))
    inner_html = "".join(inner_content_list)
    inner_html = inner_html.replace('<strong>', '<b>').replace('</strong>', '</b>')
    inner_html = inner_html.replace('<em>', '<i>').replace('</em>', '</i>')
    return inner_html

def convert_to_pdf(report_content: str, topic: str, filepath: str) -> str:
    try:
        margin = 1 * inch
        doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=margin, rightMargin=margin, topMargin=margin, bottomMargin=margin)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='H1', fontSize=20, fontName='Helvetica-Bold', spaceAfter=14))
        styles.add(ParagraphStyle(name='H2', fontSize=16, fontName='Helvetica-Bold', spaceAfter=12))
        styles.add(ParagraphStyle(name='H3', fontSize=14, fontName='Helvetica-Bold', spaceAfter=10))
        styles.add(ParagraphStyle(name='Body', fontSize=11, fontName='Helvetica', leading=14, spaceAfter=10, alignment=4))
        styles.add(ParagraphStyle(name='List', fontSize=11, fontName='Helvetica', leading=14, leftIndent=20, spaceAfter=5, bulletIndent=10))

        flowables = []
        topic_html = topic.replace('\n', '<br/>')
        title_style = styles['H1']
        title_style.alignment = 1 
        flowables.append(Paragraph(topic_html, title_style))
        flowables.append(Spacer(1, 0.25 * inch))

        html_content = markdown.markdown(report_content, extensions=['nl2br'])
        tree = html.fromstring(f"<html><body>{html_content}</body></html>")
        
        for el in tree.xpath('//body/*'):
            inner_html = _get_inner_html_for_reportlab(el)
            inner_html = inner_html.replace('<br>', '<br/>')
            
            if el.tag == 'h1': flowables.append(Paragraph(inner_html, styles['H1']))
            elif el.tag == 'h2': flowables.append(Paragraph(inner_html, styles['H2']))
            elif el.tag == 'h3': flowables.append(Paragraph(inner_html, styles['H3']))
            elif el.tag == 'p' and inner_html.strip(): flowables.append(Paragraph(inner_html, styles['Body']))
            elif el.tag in ['ul', 'ol']:
                list_counter = 1
                for li in el.xpath('.//li'):
                    li_inner_html = _get_inner_html_for_reportlab(li).replace('<br>', '<br/>')
                    if li_inner_html.strip():
                        bullet = "&bull; " if el.tag == 'ul' else f"{list_counter}. "
                        if el.tag == 'ol': list_counter += 1
                        flowables.append(Paragraph(f"{bullet}{li_inner_html}", styles['List']))
        
        doc.build(flowables)
        return f"Success: PDF file created at {filepath}"
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return f"Error creating PDF file: {e}"