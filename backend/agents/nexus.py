from typing import List
from .utils import call_model_async, LEGION_MODELS
from .tools import perform_web_search

async def agent_nexus(drafts: List[str], section_title: str) -> str:
    print(f"    >>> The Nexus is synthesizing {len(drafts)} drafts...")
    
    combined_input = ""
    for i, draft in enumerate(drafts):
        combined_input += f"\n--- DRAFT {i+1} ---\n{draft}\n"
    
    # Step 1: Check for Insufficient Data
    check_prompt = (
        f"Review these drafts for the section '{section_title}'.\n"
        "Do they inherently lack specific data/stats required for a high-quality section?\n"
        "Output 'MISSING: <search_query>' if data is missing.\n"
        "Output 'SUFFICIENT' if they are good enough."
    )
    
    check_resp = await call_model_async(LEGION_MODELS[0], "Research Director", combined_input + "\n" + check_prompt)
    
    if "MISSING:" in check_resp:
        query = check_resp.replace("MISSING:", "").strip()
        print(f"    >>> Nexus detected missing data. Recursive Search: {query}")
        print("    > (Fetching fresh data from the web...)")
        new_data = await perform_web_search(query, max_results=3)
        combined_input += f"\n\n--- FRESH WEB DATA ---\n{new_data}\n"

    # Step 2: Final Synthesis
    prompt = (
        f"Synthesize the following {len(drafts)} drafts for the section '{section_title}' into ONE superior, cohesive master draft.\n"
        "RULES:\n"
        "1. Remove all repetition/redundancy.\n"
        "2. Keep the BEST stats, tables, and insights from ALL drafts.\n"
        "3. Maintain a unified professional tone.\n"
        "4. Structure with clear Markdown headers.\n"
        "5. Preserve all inline citation brackets (e.g. [1], [2]) and align them accurately with their facts.\n"
        "6. Output ONLY the synthesized content."
    )
    
    return await call_model_async(LEGION_MODELS[0], "You are The Nexus, a Master Synthesizer.", combined_input + prompt)
