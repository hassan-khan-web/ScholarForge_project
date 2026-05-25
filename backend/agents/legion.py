from typing import List
import asyncio
from .utils import call_model_async, LEGION_MODELS

async def agent_legion(section_title: str, topic: str, context: str) -> List[str]:
    print(f"    >>> The Legion is mobilizing for: {section_title}")
    
    prompt = (
        f"Write a detailed, academic section titled '{section_title}' for a report on '{topic}'.\n"
        f"Context:\n{context[:10000]}\n\n"
        "Requirements:\n"
        "1. Be dense, factual, and analytical.\n"
        "2. Use Markdown formatting (## Headers, Tables).\n"
        "3. Focus on specific stats, numbers, and case studies found in the context.\n"
        "4. CITATIONS: You MUST cite specific sources from the context using inline bracket citations (e.g., [1], [2]) directly corresponding to the SOURCE [1], SOURCE [2] indices."
    )
    
    tasks = []
    for model in LEGION_MODELS:
        tasks.append(call_model_async(model, "You are a specialized Research Agent.", prompt))
    
    results = await asyncio.gather(*tasks)
    # Filter out failures
    valid_results = [r for r in results if r and "Agent Failure" not in r and len(r) > 100]
    
    if not valid_results:
        # Fallback if all fail
        return [await call_model_async(LEGION_MODELS[0], "Research Agent", prompt)]
        
    return valid_results
