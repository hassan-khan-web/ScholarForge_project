"""
This file stores the prompt templates for various report formats.
The AI_engine.py will import this file to access the formats.
"""

# ---
# --- THIS IS THE FIX ---
# ---
# The default format is now an empty string. The placeholder in the
# report_generator.html file will be shown instead.
DEFAULT_FORMAT = ""
# ---
# ---

# Format 1: Literature Review
LITERATURE_REVIEW = """
# 1. Introduction (Approx. 1-2 pages)
## 1.1. Background and Context
(Introduce the broad research topic and explain why it is a significant area of study. Establish the "problem" that the research is trying to address.)
## 1.2. Rationale and Justification for Review
(Explain why this literature review is necessary. For example, is there new conflicting research? Has there been a recent surge in interest? Is the existing literature scattered?)
## 1.3. Scope and Delimitations
(Clearly state the boundaries of this review. What is included? e.g., "This review focuses on research from the last 10 years...")
(What is not included? e.g., "...and excludes research focused purely on the financial/market aspects.")
## 1.4. Guiding Research Question(s)
(State the central question(s) this review aims to answer. For example: "What is the current consensus on...?", "What are the primary methodological conflicts in...?", "What gaps exist in...?")
## 1.5. Review Methodology
(Briefly explain how the sources for the review were gathered—this will be based on the provided summary. e.g., "This review synthesizes findings from key academic, governmental, and industry sources...")
## 1.6. Structure of the Review
(Provide a "roadmap" for the rest of the report, briefly mentioning the main themes you will discuss. e.g., "The review is organized into four main themes: [Theme A], [Theme B]...")
# 2. Main Body: Thematic Synthesis (Approx. 10-12 pages)
[INSTRUCTION TO AI: You must identify 4-5 major themes, debates, or methodological trends from the provided summary. Create a descriptive title for each theme. For *each* theme, you MUST follow the 5-part sub-structure below. This is the most important part of the report.]
## 2.1. Theme A: [Create a Descriptive Thematic Title Here]
### 2.1.1. Definition and Significance: (Define this theme and explain why it is a critical component of the broader topic.)
### 2.1.2. Foundational Works and Key Theories: (Discuss the seminal studies or theories that established this theme.)
### 2.1.3. Synthesis of Current Findings: (Discuss what the current research says. Compare and contrast the findings. What do authors agree on? Where do they disagree?)
### 2.1.4. Methodological Approaches and Critiques: (How are researchers studying this theme? What are the common methods used (e.g., quantitative, qualitative, case studies)? What are the strengths and limitations of these methods?)
### 2.1.5. Summary of Theme A: (Provide a concluding summary of the "state of the art" for this specific theme before moving to the next.)
## 2.2. Theme B: [Create a Descriptive Thematic Title Here]
### 2.2.1. Definition and Significance:
### 2.2.2. Foundational Works and Key Theories:
### 2.2.3. Synthesis of Current Findings: (Compare/contrast...)
### 2.2.4. Methodological Approaches and Critiques:
### 2.2.5. Summary of Theme B:
## 2.3. Theme C: [Create a Descriptive Thematic Title Here]
### 2.3.1. Definition and Significance:
### 2.3.2. Foundational Works and Key Theories:
### 2.3.3. Synthesis of Current Findings: (Compare/contrast...)
### 2.3.4. Methodological Approaches and Critiques:
### 2.3.5. Summary of Theme C:
## 2.4. Theme D: [Create a Descriptive Thematic Title Here]
### 2.4.1. Definition and Significance:
### 2.4.2. Foundational Works and Key Theories:
### 2.4.3. Synthesis of Current Findings: (Compare/contrast...)
### 2.4.4. Methodological Approaches and Critiques:
### 2.4.5. Summary of Theme D:
[Instruction to AI: Add more themes (e.g., Theme E, Theme F) as needed to build a comprehensive, 15-page report based on the richness of the summary.]
# 3. Conclusion and Future Directions (Approx. 1-2 pages)
## 3.1. Summary of Key Insights
(Provide a high-level summary that answers the Guiding Research Question(s) from Section 1. What is the overall picture of the research field?)
## 3.2. Identification of Gaps in the Literature
(This is critical. Based on your synthesis, what is missing? What do we still not know? Are there populations, methods, or questions that are consistently overlooked?)
## 3.3. Recommendations for Future Research
(Based directly on the gaps identified above, propose specific, actionable ideas for what researchers should study next.)
## 3.4. Final Concluding Remarks
(End with a final, powerful statement about the importance of this field and the implications of the current state of research.)
# 4. References
## 4.1. Bibliography
(List all the sources [1], [2], [3], etc., that were cited in the report.)
"""


# Format 2: Case Study
CASE_STUDY = """
## **1.0 Executive Summary**
(A 1-page, dense summary of the entire case. Must include the central problem, the methodology, the key findings, and the main conclusion/lessons learned.)
## **2.0 Table of Contents**
(Generate a full table of contents based on this structure.)
## **3.0 Introduction**
### 3.1. Identification of the Case
(Introduce the subject of the case study—who, what, where, and when. Clearly state the case.)
### 3.2. Research Problem / Central Question
(State the *purpose* of the study. What is the central question this case study seeks to answer? e.g., "How did [Person] achieve [Outcome] despite [Obstacle]?" or "What factors led to the [Event]?")
### 3.3. Significance of the Case
(Explain *why* this case is important to study. What broader insights or lessons can be learned? Why does it matter?)
### 3.4. Methodology
(Describe the "research" method. e.g., "This case study is a qualitative analysis based on a synthesis of publicly available data, historical records, expert analysis, and (if RAG-based) an analysis of [X] primary sources...")
### 3.5. Report Structure
(Briefly outline the remaining sections of the report.)
## **4.0 Background and Context**
### 4.1. Historical / Environmental Context
(Set the scene. What was the world like when this case began? What was the industry, political climate, or social environment?)
### 4.2. Key Actors and Entities
(Detailed profile of the person, group, or key players involved *before* the main events. What was their background, their motivations, and their initial position?)
### 4.3. The "Trigger" Event
(What specific incident, decision, or change kicked off the main events of this case study? Describe it in detail.)
## **5.0 Detailed Analysis of the Case**
(This is the core of the report. Break the case down into chronological phases or key themes.)
### 5.1. Phase 1: [Descriptive Title, e.g., "The Initial Challenge and Response"]
#### 5.1.1. Key Actions and Decisions
(Describe the actions taken by the case subject in this phase.)
#### 5.1.2. Obstacles and Facilitators
(What challenges did they face? What (or who) helped them?)
#### 5.1.3. Immediate Outcomes and Repercussions
(What were the results of this phase? Did it succeed or fail?)
### 5.2. Phase 2: [Descriptive Title, e.g., "The Strategic Pivot" or "The Mid-Point Crisis"]
#### 5.2.1. Key Actions and Decisions
(Describe the next set of actions as the case evolved.)
#### 5.2.2. Obstacles and Facilitators
(What new challenges and new allies emerged?)
#### 5.2.3. Immediate Outcomes and Repercussions
(What were the results of this second phase?)
### 5.3. Phase 3: [Descriptive Title, e.g., "Consolidation and Long-Term Impact"]
#### 5.3.1. Key Actions and Decisions
(Describe the final set of actions that led to the case's conclusion.)
#### 5.3.2. Obstacles and Facilitators
(What were the final hurdles or game-changing advantages?)
#### 5.3.3. Final Outcomes and Long-Term Impact
(What was the final, lasting result of this phase?)
## **6.0 Discussion and Implications**
### 6.1. Analysis of Key Factors
(Analyze *why* the events happened as they did. What were the 3-5 most critical factors for the success, failure, or outcome of this case?)
### 6.2. Application of [Relevant Theory/Framework]
(This is critical for a deep analysis. Apply a known theory. e.g., "Applying SWOT Analysis to [Company]" or "Analyzing [Person's] decisions through the lens of 'Game Theory'...")
### 6.3. Broader Implications
(What does this case study teach us about the wider world, the industry, leadership, or society?)
## **7.0 Conclusion and Lessons Learned**
### 7.1. Summary of Findings
(Concisely restate the answer to the "Central Question" from section 3.2.)
### 7.2. Key Lessons Learned
(Provide a bulleted list of 5-7 actionable, insightful lessons that a reader can take away from this case.)
### 7.3. Limitations of this Study
(Acknowledge any weaknesses. e.g., "This analysis is limited by its reliance on public data and cannot account for private conversations...")
### 7.4. Suggestions for Future Research
(What new questions arise from this case? What could another researcher study next?)
## **8.0 References**
(Generate a bibliography of sources used or relevant to the case. e.g., "List 15-20 relevant books, articles, and reports in APA format.")
## **9.0 Appendix (Optional)**
### Appendix A: Detailed Timeline of Events
### Appendix B: Biographies of Key Actors
### Appendix C: [Relevant Data, e.g., Financials, Maps, etc.]
"""


# Format 3: Business White Paper
BUSINESS_WHITE_PAPER = """
You are an expert business strategist and persuasive writer. Your task is to generate a comprehensive 15-page "Business White Paper" on a given topic. The goal is not just to inform, but to persuade a business decision-maker to adopt a specific technology, product, or viewpoint.
You must follow this exact 15-page structure. Be detailed, professional, and use clear, persuasive language. Use business-centric headings.
---
# [Report Title: A Persuasive Title, e.g., "The AI Revolution in Supply Chain: Why [Product] is the Key to Unlocking Efficiency"]
## Page 1: Title Page
- Report Title
- Subtitle (e.g., "A Persuasive Analysis for Business Leaders")
- Prepared by: [Your Application's Name]
- Date: [Current Date]
## Page 2: Table of Contents
- (Generate a list of all major headings and sub-headings from this structure)
## Page 3: The Executive Summary
- **This is the entire white paper in one page.**
- **The Problem:** A 1-paragraph summary of the critical business challenge.
- **The Status Quo:** A 1-paragraph summary of why current solutions are failing.
- **The Solution:** A 1-paragraph introduction to the [Product/Technology/Viewpoint].
- **The Value Proposition:** A 2-3 paragraph summary of the key benefits, ROI, and competitive advantages.
- **Conclusion:** A single, strong concluding statement.
---
# Part 1: The Problem & The Stakes
## Pages 4-5: Introduction: The Shifting Landscape
- **Context:** Set the stage. Describe the current industry or market. What big change is happening? (e.g., "The post-pandemic supply chain is facing unprecedented volatility...")
- **The Critical Business Challenge:** A deep dive into the specific, expensive, and urgent problem that the target reader is facing. Use data or statistics if possible.
- **The "Cost of Inaction":** What happens if the reader does nothing?
    - Financial Implications (e.g., "Wasted spend, lost revenue...")
    - Competitive Risks (e.g., "Falling behind more agile competitors...")
    - Operational Inefficiencies (e.g., "Continued bottlenecks, manual errors...")
## Pages 6-7: The Status Quo: Why Current Solutions Fail
- **An Overview of Today's "Best Practices":** Describe 2-3 common ways companies try to solve this problem today (e.g., "Legacy Software," "Manual Processes," "Competitor A's Approach").
- **The "Solution Gap":** For each of those practices, detail exactly why they are no longer good enough.
    - **Limitation 1:** (e.g., "Lack of Scalability")
    - **Limitation 2:** (e.g., "Prohibitive Costs")
    - **Limitation 3:** (e.g., "Poor Integration & Data Silos")
- **The Concluding Argument:** Summarize *why* a new approach is not just "nice to have," but "need to have."
---
# Part 2: The Solution & The Proof
## Pages 8-10: The New Paradigm: Introducing [Product/Technology/Viewpoint]
- **This is the core of the paper. Be detailed.**
- **Our Solution: A New Framework for Success:** Introduce your product or viewpoint as the definitive answer to the "Solution Gap" you just identified.
- **How It Works (The "Secret Sauce"):** Explain the core concepts of your solution in clear, business-friendly terms. Avoid overly technical jargon.
    - (e.g., "Instead of reactive analysis, our solution uses predictive AI...")
    - (e.g., "Our framework is built on three core pillars: Integration, Prediction, and Automation...")
- **Key Features & Their Business Benefits (3-4 pages total):**
    - **Feature 1:** [Name of Feature]
    - **Business Benefit:** [Explain in clear terms what this feature *does* for the business, e.g., "This automated-reporting feature eliminates 40 hours of manual work per month, freeing up your team for strategic analysis."]
    - **Feature 2:** [Name of Feature]
    - **Business Benefit:** [e.g., "Our predictive-AI engine forecasts demand with 95% accuracy, reducing overstocking costs by 30%."]
    - **Feature 3:** [Name of Feature]
    - **Business Benefit:** [e.g., "The unified dashboard provides a single source of truth, ending data silos and enabling faster decisions."]
## Pages 11-12: Proof: Real-World Validation
- **This section builds trust. Be specific and create 2-3 "mini-stories."**
- **Case Study 1: [Name of a Hypothetical Company, e.g., "Global Logistics Inc." ]**
    - **The Challenge:** What problem did they have?
    - **The Implementation:** How did they use your solution?
    - **The Measurable Results:** (e.g., "Achieved a 25% reduction in shipping costs," "Increased on-time delivery from 80% to 99%," "Saw full ROI in 6 months.")
- **Case Study 2: [Name of another Hypothetical Company, e.g., "Mid-Market Retail Co." ]**
    - **The Challenge:** A different problem.
    - **The Implementation:** A different use case.
    - **The Measurable Results:** (e.g., "Cut inventory errors by 50%," "Improved team productivity by 4x.")
---
# Part 3: The Call to Action
## Page 13: The Competitive Advantage
- **Why [Solution] is the Future:** A strong, forward-looking argument. Reiterate how this solution moves the reader from a reactive to a proactive state.
- **The New Business Model:** Briefly explain how adopting this solution doesn't just fix a problem but enables new opportunities (e.g., "You're not just saving money; you're building a more resilient, intelligent business.")
- **ROI & Value Proposition Summary:** A final, hard-hitting summary of the business value.
## Page 14: Your Next Steps: How to Get Started
- **This is the Call to Action.**
- **Step 1: The Assessment:** (e.g., "Contact us for a free, no-obligation assessment of your current system.")
- **Step 2: The Demo:** (e.g., "Schedule a personalized demo to see the platform in action.")
- **Step 3: The Roadmap:** (e.g., "Let our experts build a custom implementation roadmap for your business.")
- **Conclusion:** A final, confident, and persuasive closing paragraph.
## Page 15: About [Your Company/Organization] & References
- **About Us:** A 1-2 paragraph "boilerplate" explaining who you are and why you are the credible expert on this topic.
- **Contact Information:** (e.g., "Visit our website at [Website]", "Email us at [Email]").
- **References:** (List any sources, data, or studies mentioned in the report).
"""


# Format 4: Technical Manual
TECHNICAL_MANUAL = """
Part 1: Front Matter (Pages 1-2)
This section onboards the user and sets the stage.
Page 1: Title Page & Table of Contents
1.0 [Report Title]: A Technical Manual
Subtitle: Installation, Operation, and Maintenance Guide
Product Version: [e.g., v2.5]
Publication Date: [Current Date]
1.1 Table of Contents
(This should be a detailed, multi-level list of all sections and sub-sections you are generating below.)
Page 2: Introduction & Safety
2.0 Introduction
2.1 Purpose of This Manual: (e.g., "This document provides detailed instructions for the installation, configuration, and operation of [Product Name]...")
2.2 Intended Audience: (e.g., "This manual is for system administrators, developers, and technicians. A basic understanding of [X] and [Y] is assumed.")
2.3 Product Overview: (A 2-3 paragraph summary of the product, its key features, and its purpose.)
2.4 What's New in This Version: (List 3-5 key changes from the previous version.)
2.5 Critical Safety Warnings
(Use 2-3 highly specific warnings. Don't be generic. Example: "DANGER: Always disconnect the primary power source before accessing the internal-service panel to prevent severe electrical shock.")
Part 2: Core Procedures (Pages 3-12)
This is the main body of the manual and the easiest place to add substantial, high-value content.
Pages 3-4: Installation & Setup
3.0 Getting Started: Installation and Configuration
3.1 System Requirements: (This is key. Be detailed.)
Hardware: (e.g., "Minimum 8-Core CPU, 32GB RAM, 100GB SSD Storage")
Software: (e.g., "Windows Server 2022+, or Ubuntu 24.04 LTS. Requires Python 3.11+, PostgreSQL 16+")
3.2 Required Tools and Materials:
(List everything needed, e.g., "Cross-head (Phillips) screwdriver (PH2)," "SSH Client (e.g., PuTTY)," "Admin-level API Key from [Service].")
3.3 Installation Package Contents:
(List the files included, e.g., install.sh, config.template.yml, README.md)
3.4 Step-by-Step Installation Guide
(This is where you expand. Provide separate guides for different environments.)
3.4.1 Installation on Windows Server
(Detailed, numbered steps with command examples.)
3.4.2 Installation on Ubuntu Linux
(Detailed, numbered steps with command examples.)
3.5 Initial Configuration
(Walk through the config.template.yml file, explaining 5-10 key parameters and what they do.)
3.6 Validating the Installation
(e.g., "Run the following command: [product_name] --health-check." Show the expected output.)
Pages 5-9: Operational Procedures (The Core)
Do not write one long "How to Use" section. Break every major feature into its own 4.X subsection.
4.0 Operating Procedures: A Feature-by-Feature Guide
4.1 Feature 1: [Name of First Core Feature]
Introduction: (What is this feature?)
Scenarios: (When would a user use this?)
Step-by-Step Instructions: (A numbered list on how to use it, with screenshots or code block examples.)
Tips & Best Practices: (e.g., "Always batch process more than 1,000 records to maximize efficiency.")
4.2 Feature 2: [Name of Second Core Feature]
Introduction:
Scenarios:
Step-by-Step Instructions: (Include different parameters and examples.)
Common Mistakes: (e.g., "Do not use the --force flag on a production database.")
4.3 Feature 3: [Name of Third Core Feature]
(Repeat the structure: Introduction, Scenarios, Instructions...)
4.4 Feature 4: [Name of Fourth Core Feature]
(Repeat the structure...)
4.5 Advanced Operations: [Name of a Complex Feature]
(This section is for a power-user, explaining a complex workflow that combines multiple features.)
Pages 10-12: Maintenance & Troubleshooting
5.0 System Maintenance
5.1 Daily Maintenance Tasks: (e.g., "Check log files for errors," "Verify disk space.")
5.2 Weekly Maintenance Tasks: (e.g., "Run database cleanup script," "Perform security scan.")
5.3 Backing Up Your Data: (Step-by-step guide on how to perform a full backup.)
5.4 Restoring from a Backup: (Step-by-step guide to recover from a failure.)
6.0 Troubleshooting Guide
(Use a "Problem/Cause/Solution" format. This adds a lot of value.)
6.1 Problem: Service Fails to Start
Symptoms: (Error message "Service failed with code 1066.")
Possible Causes: (1. Incorrect port in config. 2. Database not running.)
Solution(s): (Numbered steps to check the port and database status.)
6.2 Problem: Slow API Response Times
Symptoms: (GET requests take >5 seconds.)
Possible Causes: (1. Database index fragmentation. 2. Network latency.)
Solution(s): (Steps to re-index the database and use ping to test latency.)
6.3 Problem: [Another Common Error]
(Repeat the Symptoms/Causes/Solutions format.)
Part 3: Back Matter (Pages 13-15)
This section provides reference material that adds professional polish and valuable density.
Page 13: Technical Specifications
7.0 Technical Specifications
7.1 Performance Metrics: (e.g., "Handles 5,000 API requests per minute," "Data processing speed: 200MB/s.")
7.2 Security Standards: (e.g., "All data encrypted at rest (AES-256)," "Complies with OAuth 2.0.")
7.3 Network Ports Used: (A table of ports and their purpose, e.g., 8080/tcp, 5432/tcp.)
7.4 Configuration File Parameters:
(A large table listing all parameters from the config file, their default value, and a description.)
Page 14: Appendices
8.0 Appendix A: Error Code Reference
(A large table of error codes and their meanings.)
(e.g., E-1001: Database Connection Error, E-2004: Invalid API Key.)
8.1 Appendix B: Sample Configuration Files
(Provide 2-3 full code-block examples of config files for different scenarios, e.g., "Development Config," "Production Config.")
Page 15: Glossary & Contact
9.0 Glossary
(Define 15-20 technical terms, acronyms, and product-specific jargon used throughout the manual.)
10.0 Contact & Support
10.1 Getting Help: (e.g., "Please visit our support portal at...")
10.2 License Information: (A brief legal notice or a copy of the EULA/License.)
"""


# Format 5: Journalistic/News Article
JOURNALISTIC_ARTICLE = """
Part 1: The Inverted Pyramid (Pages 1-2)
This is the "hard news" summary. Your reader gets all the essential facts immediately.
## Section 1: The Lead (Page 1)
The most important information. This section answers the classic 5 Ws and 1 H.
Headline: The main, declarative statement.
The Lead (1-2 Paragraphs): This is the core of the inverted pyramid. It must state:
Who: Who is involved?
What: What happened? (The key event/finding)
When: When did it happen?
Where: Where did it take place?
Why: Why did it happen? (The brief, top-level reason)
How: How did it happen? (The brief overview of the method)
## Section 2: The "Nut Graf" (Page 1-2)
This is the single most important transition. It's a "nutshell paragraph" that answers the reader's question: "So what? Why should I read 14 more pages?"
The Big Picture: Explain the wider context, significance, and stakes of the topic.
The "So What?": State the main argument or thesis of your 15-page report.
The Road Map: Briefly (1-2 sentences) preview the sections to come ("This report will explore the history, analyze the key players, and detail the future implications...").
## Section 3: The Body (Page 2)
The most important supporting details that expand directly on the lead.
Key Quotes: The most powerful quotes from your primary sources.
Essential Data: The most critical statistics or data points.
Immediate Context: Background information that is essential to understanding the lead.
Part 2: The Long-Form Narrative Body (Pages 3-13)
You now abandon the inverted pyramid and transition to a "feature" or "kabob" structure. You will organize the rest of the report by themes, not by "descending importance." This is where you provide the deep analysis.
## Section 4: The Human Element / Anecdote (Page 3-4)
The "Kabob" Skewer: Start with a specific, compelling anecdote or case study.
Introduce a Character: Tell the story of a person or group directly affected by the topic. This humanizes the data and makes the reader care.
The Micro-Story: Show the problem in action, rather than just telling.
## Section 5: The Deep Dive: History & Context (Page 5-7)
Background: Go deep into the history. How did we get here? What events led to this?
Literature Review (Journalistic Style): What have other experts and publications said about this?
Analysis of the Past: Explain the precedents and historical patterns.
## Section 6: The Core Analysis: The "Meat" (Page 8-11)
This is the main body of your report. You can break this into multiple sub-sections.
Theme 1: The Key Players: Profile the major organizations, people, or technologies involved. What are their motivations?
Theme 2: The Process: A detailed, chronological explanation of the "how." (e.g., how the technology works, how the policy was created, etc.).
Theme 3: The Data & Evidence: This is where you put your charts, graphs, and detailed findings. You can present conflicting information and analyze it.
## Section 7: The "Other Side" / Counter-Argument (Page 12-13)
Conflicting Information: Acknowledge and explore the counter-arguments.
Obstacles & Challenges: What are the main points of disagreement or difficulty?
Alternative Perspectives: Include quotes and data from experts who disagree with your main findings. This builds credibility.
Part 3: The Conclusion (Pages 14-15)
You must never "cut from the bottom" in this style. The conclusion is critical.
## Section 8: The "Circle Kicker" (Page 14)
Return to the Anecdote: Revisit the person or story you introduced in Section 4.
Show Resolution (or lack thereof): How did their story turn out? How does their micro-story reflect the larger findings of your report? This provides a powerful, satisfying ending.
## Section 9: The Look Forward (Page 15)
Conclusion: A final summary of your thesis and most important findings (do not just repeat the lead).
Future Implications: What happens next? What are the unanswered questions?
The Final "Kicker": End with a single, powerful, forward-looking thought, quote, or image that leaves a lasting impression on the reader.
"""

# This dictionary maps the dropdown values to the template variables.
# This is what AI_engine.py will import and use.
FORMAT_TEMPLATES = {
    "custom": DEFAULT_FORMAT,
    "literature_review": LITERATURE_REVIEW,
    "case_study": CASE_STUDY,
    "business_white_paper": BUSINESS_WHITE_PAPER,
    "technical_manual": TECHNICAL_MANUAL,
    "journalistic_article": JOURNALISTIC_ARTICLE,
}