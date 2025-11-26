"""
This file stores the prompt templates for various report formats.
The AI_engine.py will import this file to access the formats.
"""

DEFAULT_FORMAT = ""

# Format 1: Literature Review (Condensed)
# We removed the hardcoded "Theme A, B, C" and "2.1.1, 2.1.2" nesting.
LITERATURE_REVIEW = """
# 1. Introduction
## 1.1. Background and Rationale
## 1.2. Scope and Methodology
# 2. Main Body: Thematic Synthesis
[INSTRUCTION TO AI: This is the core of the report. Based on the target page count, generate 3 to 5 MAJOR sections representing key themes in the literature. Do NOT use sub-sub-headings like 2.1.1. Keep it to Main Headers (e.g., "2. The Evolution of AI", "3. Economic Impacts").]
# 3. Critical Discussion
## 3.1. Comparison of Perspectives
## 3.2. Identification of Gaps
# 4. Conclusion
## 4.1. Summary of Insights
## 4.2. Future Research Directions
# 5. References
"""

# Format 2: Case Study (Condensed)
# We removed the hardcoded "Phase 1, Phase 2, Phase 3" structure.
CASE_STUDY = """
# 1. Executive Summary
# 2. Introduction
## 2.1. Case Subject Profile
## 2.2. Problem Statement
# 3. Context and Background
[INSTRUCTION TO AI: Describe the environment, history, or market conditions before the main event.]
# 4. Analysis of the Case
[INSTRUCTION TO AI: Break the case down into chronological phases or key challenges. Generate 3 to 4 sections appropriate for the requested report length. e.g., "4. The Initial Challenge", "5. The Strategic Pivot", "6. The Outcome".]
# 5. Key Findings and Lessons
## 5.1. Success Factors
## 5.2. Failures and Bottlenecks
# 6. Conclusion
"""

# Format 3: Business White Paper (Condensed)
# Removed the specific "Page 1, Page 2" breakdown which confused the AI.
BUSINESS_WHITE_PAPER = """
# 1. Executive Summary
# 2. The Market Context
## 2.1. Current Trends
## 2.2. The Business Challenge
# 3. Analysis of Solutions
[INSTRUCTION TO AI: Compare current legacy solutions vs. the proposed new solution. Generate distinct sections analyzing the pros, cons, and ROI of adopting the new approach.]
# 4. Proposed Framework / Solution
[INSTRUCTION TO AI: Detail the solution. Break this into 2 or 3 descriptive sections focusing on implementation and benefits.]
# 5. Real-World Implications (Case Examples)
# 6. Strategic Recommendations & Call to Action
"""

# Format 4: Technical Manual (Condensed)
TECHNICAL_MANUAL = """
# 1. Overview
## 1.1. Purpose and Scope
## 1.2. System Requirements
# 2. Installation and Setup
[INSTRUCTION TO AI: Provide a step-by-step guide for installation.]
# 3. Core Features and Operations
[INSTRUCTION TO AI: Identify the 3-5 most important features of this technology. Create a dedicated section for each feature explaining how it works and how to use it.]
# 4. Maintenance and Troubleshooting
## 4.1. Routine Maintenance
## 4.2. Common Issues and Fixes
# 5. Appendix and Specs
"""

# Format 5: Journalistic Article (Condensed)
JOURNALISTIC_ARTICLE = """
# 1. The Lead (Headline & Hook)
# 2. The Nut Graf (Context & Significance)
# 3. The Narrative Body
[INSTRUCTION TO AI: Tell the story. Break the body into 3-4 thematic or chronological sections. Use descriptive, catchy headers. Quote key figures and cite data.]
# 4. Counter-Perspectives
[INSTRUCTION TO AI: Discuss alternative viewpoints or challenges.]
# 5. Conclusion (The Kicker)
"""

FORMAT_TEMPLATES = {
    "custom": DEFAULT_FORMAT,
    "literature_review": LITERATURE_REVIEW,
    "case_study": CASE_STUDY,
    "business_white_paper": BUSINESS_WHITE_PAPER,
    "technical_manual": TECHNICAL_MANUAL,
    "journalistic_article": JOURNALISTIC_ARTICLE,
}