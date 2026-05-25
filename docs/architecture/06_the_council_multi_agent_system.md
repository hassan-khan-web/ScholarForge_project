# ScholarForge: The Council Multi-Agent System

This chapter examines the collaborative writing loop managed by `backend/council.py` and the agent modules in `backend/agents/`. This multi-agent framework manages outline planning and drafting tasks.

---

## Why the Council?

In standard AI generation systems, a single LLM call is responsible for researching, structuring, drafting, and reviewing a section. This can lead to a mix of high-quality writing and generic summaries or unsourced claims.

The Council addresses this by dividing these tasks among specialized agents:

```
           ┌──────────────────────────────────────────────────┐
           │                     Legion                       │
           │ (Parallel Drafting: 5 Models write draft options)│
           └────────────────────────┬─────────────────────────┘
                                    │
                                    ▼
           ┌──────────────────────────────────────────────────┐
           │                      Nexus                       │
           │ (Synthesis: Merges drafts & checks for gaps)     │
           └────────────────────────┬─────────────────────────┘
                                    │
                                    ▼
       ┌──>┌──────────────────────────────────────────────────┐
       │   │                   Inquisitor                     │
       │   │ (Fact-Checker: Scrutinizes claims & scores drafts)│
       │   └────────────────────────┬─────────────────────────┘
       │                            │
  No,  │                            │ Approved (Score > 85)
  Low  │                            │ or Loop Limit (3) Reached
  Score│                            │
       │                            ▼
       │   ┌──────────────────────────────────────────────────┐
       └───┤                     Artisan                      │
           │ (Master Writer: Polishes text & fixes critique)  │
           └────────────────────────┬─────────────────────────┘
                                    │
                                    ▼
                            [Finalized Section]
```

---

## The Four Agent Roles

### 1. The Legion (`backend/agents/legion.py`)
When writing a section, the Legion launches five models in parallel:
1. `google/gemini-2.0-flash-001` (Research Director)
2. `llama-3.3-70b-versatile` (Reasoning Specialist)
3. `nvidia/nemotron-3-nano-30b-a3b:free` (Efficiency Expert)
4. `llama-3.1-8b-instant` (Artisan writer)
5. `llama-3.1-8b-instant` (Inquisitor reviewer)

Using `asyncio.gather`, the Legion generates five independent drafts based on the initial topic context. It filters out any API errors or empty drafts, passing only valid proposals to the next step.

### 2. The Nexus (`backend/agents/nexus.py`)
The Nexus is responsible for synthesis and gap analysis:
* It reviews the Legion's drafts to check if they lack specific statistics or case studies.
* If gaps are found, it outputs a `MISSING: <search_query>` instruction.
* This instruction triggers an asynchronous Tavily search to fetch the missing details, which are appended to the context before the drafts are merged into a single master draft.

### 3. The Inquisitor (`backend/agents/inquisitor.py`)
The Inquisitor acts as a fact-checker:
* It identifies specific claims in the draft that require verification.
* It searches the web to check the accuracy of these claims.
* It evaluates the draft for logical fallacies or repetition and returns a JSON response containing:
  * `status`: `"APPROVED"` or `"REJECTED"`.
  * `score`: A rating from 0 to 100.
  * `critique`: Detailed feedback for improvements.

### 4. The Artisan (`backend/agents/artisan.py`)
The Artisan is the writer and editor:
* It rewrites sections to improve flow and readability.
* It incorporates feedback from the Inquisitor's critiques while preserving key facts and statistics.
* It performs a final styling pass before the section is approved.

---

## The Critique and Revision Loop

The Council coordinates these agents in a feedback loop, defined in `backend/council.py`:

```python
async def run_council(section_title: str, topic: str, context: str, update_status_callback=None) -> str:
    # 1. Mobilize Legion to write draft variants
    drafts = await agent_legion(section_title, topic, context)
    
    # 2. Synthesize drafts with Nexus
    master_draft = await agent_nexus(drafts, section_title)
    
    # 3. Iterative Optimization Loop
    max_loops = 3
    current_content = master_draft
    
    for i in range(max_loops):
        # Run Inquisitor check
        review = await agent_inquisitor(current_content, topic)
        
        # If approved with high score, polish and return
        if review.get('status') == 'APPROVED' and review.get('score', 0) > 85:
            final_polish = await agent_artisan(current_content)
            return final_polish
            
        # Otherwise, pass critique to Artisan to revise and loop again
        critique = review.get('critique', 'Improve verification.')
        current_content = await agent_artisan(current_content, critique)
    
    return current_content
```

This multi-step review process helps ensure that each section is researched, structured, and reviewed before it is added to the report. Let's move on to **Chapter 7: Celery Task Queue** to look at the background execution architecture.
