from .utils import call_model_async, LEGION_MODELS

async def agent_artisan(content: str, critique: str = "") -> str:
    print("    >>> The Artisan is refining...")
    
    prompt = (
        "Refine and Rewrite this content to be strictly ORIGINAL (0% Plagiarism) and Polished.\n"
    )
    
    if critique:
        prompt += f"ADDRESS THIS CRITIQUE: {critique}\n"
        
    prompt += (
        "1. Rephrase generic sentences to be more unique and academic.\n"
        "2. Ensure perfect flow and structure.\n"
        "3. Keep all factual data/stats and preserve all inline citation brackets (e.g. [1], [2]) exactly as they are.\n"
        "4. Output ONLY the final polished markdown."
    )
    
    return await call_model_async(LEGION_MODELS[3], "You are The Artisan, a Master Writer.", content + "\n\n" + prompt)
