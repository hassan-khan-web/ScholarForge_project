COMMON_INSTRUCTION = """
CRITICAL HEADER RULE: DO NOT use generic headers like 'Introduction', 'Background', 'Analysis', or 'Conclusion'. 
Instead, use engaging, journalistic, or action-oriented titles. 
   - BAD: "1. Introduction"
   - GOOD: "1. The Dawn of a New Era: Why Now?"
   - BAD: "Conclusion"
   - GOOD: "Final Verdict: The Path Forward"

FORMATTING RULES:
1. Use ### Sub-headers to break down the main topic into distinct sub-themes.
2. You MUST include at least one Markdown Table comparing key data points or pros/cons.
3. Keep paragraphs punchy (max 5-6 sentences).
"""

LIT_REVIEW_BASE = """
[INSTRUCTION: Generate {section_count} distinct thematic sections. 
{complexity_note}
{common_ins}]
"""

CASE_STUDY_BASE = """
[INSTRUCTION: Analyze the case phases. Generate {section_count} sections covering Strategy, Execution, and Outcome. 
{complexity_note}
{common_ins}]
"""

WHITE_PAPER_BASE = """
[INSTRUCTION: Compare solutions. Generate {section_count} sections analyzing ROI and Technical Nuance. 
{complexity_note}
{common_ins}]
"""

TECH_MANUAL_BASE = """
[INSTRUCTION: Technical Breakdown. Generate {section_count} sections covering Core Features and API usage. 
{complexity_note}
{common_ins}]
"""

ARTICLE_BASE = """
[INSTRUCTION: Narrative Flow. Generate {section_count} sections that tell the story. Use punchy, magazine-style headers.
{complexity_note}
{common_ins}]
"""

FORMAT_TEMPLATES = {
    "literature_review": LIT_REVIEW_BASE,
    "case_study": CASE_STUDY_BASE,
    "business_white_paper": WHITE_PAPER_BASE,
    "technical_manual": TECH_MANUAL_BASE,
    "journalistic_article": ARTICLE_BASE,
    "custom": LIT_REVIEW_BASE
}

def get_template_instructions(format_type: str, page_count: int) -> dict:
    """
    Returns the specific tier configuration based on page count.
    Tiers:
    - Short: 6 Pages, 3 Sections
    - Standard: 10 Pages, 4 Sections (+10% density)
    - Deep: 15 Pages, 7 Sections
    - Comprehensive: 20 Pages, 10 Sections
    - Monograph: 23+ Pages, 15 Sections
    """
    
    if page_count <= 6:
        tier = "short"
        target_sections = 3
        complexity_instruction = (
            "Structure: Concise and punchy. \n"
            "Content: Focus strictly on the 3 most critical aspects. No fluff."
        )
    
    elif page_count <= 10:
        tier = "standard"
        target_sections = 4
        complexity_instruction = (
            "Structure: Balanced depth. \n"
            "Content: Increase detail by 10%. Add specific real-world examples to every section."
        )
    
    elif page_count <= 15:
        tier = "deep"
        target_sections = 7
        complexity_instruction = (
            "Structure: Deep-Dive Analysis. \n"
            "Content: Rigorous detail. Include 'Technical Architecture' and 'Economic Impact' sections."
        )
    
    elif page_count <= 22:
        tier = "comprehensive"
        target_sections = 10
        complexity_instruction = (
            "Structure: Comprehensive Coverage. \n"
            "Content: Exhaustive. Dedicate sections to 'Risk Analysis', 'Global Competitors', and 'Long-term Forecasts'."
        )
    
    else:
        tier = "monograph"
        target_sections = 15
        complexity_instruction = (
            "Structure: Research Monograph. \n"
            "Content: Maximum density. Analyze historical context, sociological impact, and granular technical specifications."
        )

    if format_type in FORMAT_TEMPLATES:
        selected_template = FORMAT_TEMPLATES[format_type]
    else:
        selected_template = f"[INSTRUCTION: {format_type}\n{{complexity_note}}\n{{common_ins}}]"
    
    fixed_sections_estimate = 2 
    dynamic_middle_count = max(1, target_sections - fixed_sections_estimate)

    final_template = selected_template.format(
        section_count=str(dynamic_middle_count),
        complexity_note=complexity_instruction,
        common_ins=COMMON_INSTRUCTION,
        last_n=str(target_sections - 1),
        last=str(target_sections)
    )

    return {
        "template_text": final_template,
        "target_sections": target_sections,
        "tier": tier
    }