import os
import serpapi
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import requests
from bs4 import BeautifulSoup
import json
import markdown
from lxml import html
import html as html_parser # Import for escaping

# --- MODIFIED: Imports for PDF Fix ---
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
# --- END MODIFIED ---

# ---
# ---
AI_MODEL_STRING = "nvidia/nemotron-nano-12b-v2-vl:free"
# ---
# ---

SEARCH_RESULTS_COUNT = 10
MAX_RESULTS_TO_SCRAPE = 3
# ---
# --- END OF CONSTANTS ---
# ---


def _get_article_text(url: str) -> str:
    """
    Fetches and parses the main text content from a given URL.
    Returns the text or an error message.
    """
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
# --- END OF HELPER FUNCTION ---


def get_search_results(query: str) -> str:
    """
    This function uses SerpApi and is unchanged.
    """
    try:
        api_key = os.environ.get("API_KEY") 
        if not api_key:
            return "Error: API_KEY environment variable not set."
            
        params = {
            "q": query,
            "location": "India",
            "hl": "en",
            "gl": "us",
            "num": SEARCH_RESULTS_COUNT, # This line now works
            "api_key": api_key,
            "engine": "google"
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
                if i < MAX_RESULTS_TO_SCRAPE: # This line now works
                    print(f"Fetching full text from: {source_url}...")
                    full_content_text = _get_article_text(source_url)
                    full_content_text = f"\n\n--- Full Text (Source {i+1}) ---\n{full_content_text}\n--- End of Full Text ---"

                formatted_snippet = (
                    f"[{i+1}] Title: {title}\n"
                    f"Snippet: {snippet_text}\n"
                    f"Source: {source_url}"
                    f"{full_content_text}" 
                )
                snippets.append(formatted_snippet)

        return "\n\n---\n\n".join(snippets) if snippets else "No relevant search results were found."

    except Exception as e:
        return f"An unexpected error occurred during search: {e}"
# --- END OF MODIFIED FUNCTION ---


def generate_summary(search_content: str, topic: str) -> str:
    """
    Generates summary using OpenRouter API. (Unchanged)
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
            
            This output will be the ONLY source material for a full 15-page report,
            so you MUST be exhaustive and detailed. Do not skip details.
            '''
            f"Your analysis is for the topic: '{topic}'. Use citation numbers [1], [2], etc. for clarity and explain in detail."
        )

        prompt = f"Search Results:\n{search_content}"

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}", 
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": AI_MODEL_STRING, # This line now works
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

    except requests.exceptions.HTTPError as e:
        return f"OpenRouter API Error: {e.response.status_code} {e.response.text}"
    except Exception as e:
        return f"An unexpected error occurred during summarization: {e}"


def generate_report(summary: str, topic: str, user_format: str) -> str:
    """
    Generates report using OpenRouter API. (Unchanged)
    """
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return "Error: OPENROUTER_API_KEY environment variable not set."

        final_instruction = (
            "IMPORTANT: For all section headings ... "
            "Apply this descriptive logic to ALL headings and subheadings."
        )

        # ---
        # --- !!! THIS IS THE UPDATED, MORE AGGRESSIVE PROMPT !!! ---
        # ---
        system_instruction = (
            "You are a world-class research analyst and professional report writer. "
            f"Your task is to generate a comprehensive, 15-page report on the topic: '{topic}'.\n\n"
            
            # --- NEW CRITICAL REQUIREMENT ---
            "**CRITICAL CONTENT REQUIREMENT: READ AND OBEY**\n"
            "You MUST ensure **even content distribution**. The last sections of the report MUST be as detailed as the first.\n"
            "I am seeing reports that start strong but end with 1-2 line 'filler' sections. This is unacceptable.\n\n"
            "**YOUR NON-NEGOTIABLE RULE:**\n"
            "Every single sub-section (e.g., 2.1, 2.1.1, 2.1.2, 3.1) **MUST** contain a minimum of **5 to 6 full lines of text**. "
            "Do not, under any circumstances, write a 1-2 line paragraph to simply fill a heading.\n\n"
            "**I will consider the generation a FAILURE if any section is shorter than 5-6 lines.** "
            "Use your source summary to its full potential. Elaborate. Explain. Do not be brief."
            # --- END OF NEW REQUIREMENT ---
            
            "\n\nYou MUST follow this user-provided structure EXACTLY. ...\n\n"
            f"USER-PROVIDED STRUCTURE:\n{user_format}\n\n"
            f"FINAL INSTRUCTION: {final_instruction}"
        )
        # ---
        # --- END OF UPDATED PROMPT ---
        # ---

        prompt = (
            "Here is the synthesized summary of my research findings. ... "
            f"following the structure and instructions I provided.\n\nSUMMARY:\n{summary}"
        )

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}", 
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": AI_MODEL_STRING, # This line now works
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

    except requests.exceptions.HTTPError as e:
        return f"OpenRouter API Error: {e.response.status_code} {e.response.text}"
    except Exception as e:
        return f"An unexpected error occurred during report generation: {e}"
# --- END OF MODIFIED FUNCTION ---


def run_ai_engine_with_return(query: str, user_format: str, task=None) -> tuple[str, str] | str: 
    """
    Runs the full report generation pipeline. (Unchanged)
    """
    
    def _update_status(message: str):
        print(message) 
        if task:
            task.update_state(state='PROGRESS', meta={'message': message})

    if not query:
        return "Please provide a search query."
    
    if not user_format or user_format.strip() == "":
        return "Error: No report format was provided. Please select or enter a format."

    _update_status("Step 1/4: Fetching search results and full content...")
    search_content = get_search_results(query)
    if search_content.startswith(("Error:", "No relevant")):
        return f"Failed to run search pipeline: {search_content}"

    _update_status("Step 2/4: Generating structured summary...")
    summary = generate_summary(search_content, query)
    if summary.startswith(("Error:", "OpenRouter API Error:", "An unexpected error")):
        return f"Failed to summarize: {summary}"

    _update_status("Step 3/4: Generating full report...")
    report_content = generate_report(summary, query, user_format)
    
    if report_content.startswith(("Error:", "OpenRouter API Error:", "An unexpected error")):
        return f"Failed to generate report: {report_content}"
        
    _update_status("Step 4/4: Pipeline complete.")
    return search_content, report_content


def convert_to_txt(report_content: str, filepath: str) -> str:
    """ (Unchanged) """
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_content)
        return f"Success: TXT file created at {filepath}"
    except Exception as e:
        return f"Error creating TXT file: {e}"

# ---
# --- DOCX and PDF Converters with Markdown Styling
# ---

# ---
# --- THIS FUNCTION IS CORRECT ---
# ---
def add_markdown_to_doc(doc, md_text):
    """
    Parses Markdown text and adds it to the DOCX document 
    with heading and bold styling.
    """
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
            
            if el.text:
                p.add_run(el.text)
            
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
                
                if child.tail:
                    p.add_run(child.tail)
        else:
            p = doc.add_paragraph(el.text_content().strip())

# ---
# --- THIS FUNCTION IS CORRECT ---
# ---
def convert_to_docx(report_content: str, topic: str, filepath: str) -> str:
    try:
        doc = Document()
        styles = doc.styles
        
        styles['Heading 1'].font.name = 'Inter'
        styles['Heading 2'].font.name = 'Inter'
        styles['Heading 3'].font.name = 'Inter'
        styles['Normal'].font.name = 'Inter'
        styles['List Bullet'].font.name = 'Inter'
        
        styles['List Bullet'].paragraph_format.left_indent = Pt(36)
        
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


# ---
# --- THIS FUNCTION IS CORRECT ---
# ---
def _get_inner_html_for_reportlab(element):
    """
    Helper function to correctly build an HTML string for ReportLab's parser,
    including text, child tags, and tail text. (Unchanged)
    """
    inner_content_list = []
    
    if element.text:
        inner_content_list.append(html_parser.escape(element.text))
    
    for child in element:
        inner_content_list.append(html.tostring(child, encoding='unicode'))
        
        if child.tail:
            inner_content_list.append(html_parser.escape(child.tail))
            
    inner_html = "".join(inner_content_list)
    
    inner_html = inner_html.replace('<strong>', '<b>').replace('</strong>', '</b>')
    inner_html = inner_html.replace('<em>', '<i>').replace('</em>', '</i>')
    
    return inner_html


# ---
# --- !!! THIS IS THE FIXED PDF FUNCTION !!! ---
# ---
def convert_to_pdf(report_content: str, topic: str, filepath: str) -> str:
    try:
        # --- MODIFIED ---
        # We no longer use canvas. We use SimpleDocTemplate.
        margin = 1 * inch
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            leftMargin=margin,
            rightMargin=margin,
            topMargin=margin,
            bottomMargin=margin
        )

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='H1', fontSize=20, fontName='Helvetica-Bold', spaceAfter=14))
        styles.add(ParagraphStyle(name='H2', fontSize=16, fontName='Helvetica-Bold', spaceAfter=12))
        styles.add(ParagraphStyle(name='H3', fontSize=14, fontName='Helvetica-Bold', spaceAfter=10))
        styles.add(ParagraphStyle(name='Body', fontSize=11, fontName='Helvetica', leading=14, spaceAfter=10, alignment=4)) # 4 = TA_JUSTIFY
        styles.add(ParagraphStyle(name='List', fontSize=11, fontName='Helvetica', leading=14, leftIndent=20, spaceAfter=5, bulletIndent=10))

        flowables = [] # This list will hold our report content

        # --- NEW: Add the Title ---
        topic_html = topic.replace('\n', '<br/>')
        title_style = styles['H1']
        title_style.alignment = 1 # TA_CENTER
        flowables.append(Paragraph(topic_html, title_style))
        flowables.append(Spacer(1, 0.25 * inch)) # Add space after title

        # --- MODIFIED ---
        # 1. Add the 'nl2br' extension. This tells the markdown parser to
        #    convert single newlines into <br> tags, which ReportLab understands.
        html_content = markdown.markdown(report_content, extensions=['nl2br'])
        
        tree = html.fromstring(f"<html><body>{html_content}</body></html>")
        
        # --- MODIFIED: This loop now just populates the flowables list ---
        for el in tree.xpath('//body/*'):
            
            # --- NEW: Use inner_html for ALL tags to preserve bold/italic
            inner_html = _get_inner_html_for_reportlab(el)
            
            # ---
            # --- !!! THIS IS THE TRACEBACK FIX !!! ---
            # ---
            # ReportLab's parser crashes on <br> but loves <br/>
            # We must do this replacement *after* getting the inner_html.
            inner_html = inner_html.replace('<br>', '<br/>')
            # ---
            # --- !!! END OF FIX !!! ---
            # ---
            
            if el.tag == 'h1':
                if inner_html.strip(): 
                    flowables.append(Paragraph(inner_html, styles['H1']))
            elif el.tag == 'h2':
                if inner_html.strip(): 
                    flowables.append(Paragraph(inner_html, styles['H2']))
            elif el.tag == 'h3':
                if inner_html.strip(): 
                    flowables.append(Paragraph(inner_html, styles['H3']))
            
            elif el.tag == 'p':
                # This check correctly skips empty <p></p> tags from \n\n
                if inner_html.strip():
                    flowables.append(Paragraph(inner_html, styles['Body']))
                    
            elif el.tag in ['ul', 'ol']:
                # --- NEW: Added list counter for <ol> tags ---
                list_counter = 1
                for li in el.xpath('.//li'):
                    li_inner_html = _get_inner_html_for_reportlab(li)
                    # --- ALSO FIX IT FOR LIST ITEMS ---
                    li_inner_html = li_inner_html.replace('<br>', '<br/>')
                    
                    if li_inner_html.strip():
                        if el.tag == 'ul':
                            bullet = "&bull; "
                        else: # el.tag == 'ol'
                            bullet = f"{list_counter}. "
                            list_counter += 1
                        
                        flowables.append(Paragraph(f"{bullet}{li_inner_html}", styles['List']))
        
        # --- MODIFIED ---
        # Removed the entire manual drawing loop.
        # This single command builds the entire multi-page PDF correctly.
        doc.build(flowables)
        
        return f"Success: PDF file created at {filepath}"
    except Exception as e:
        # Add more detail to the error
        import traceback
        print(traceback.format_exc())
        return f"Error creating PDF file: {e}"
# --- END OF PDF FIX ---


def convert_to_references_txt(search_content: str, topic: str) -> str:
    """ (Unchanged) """
    try:
        topic_safe = "".join(c for c in topic if c.isalnum() or c in (' ', '_')).rstrip()
        filepath = f"{topic_safe}_References.txt"
        
        header = f"--- Raw Search Results and Sources for: {topic.upper()} ---\n\n"
        full_content = header + search_content
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)
        
        return f"Success: References file created at {filepath}"
    except Exception as e:
        return f"Error creating References file: {e}"