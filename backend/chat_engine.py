import os
import httpx 

AVAILABLE_MODELS = {
    "default": "openai/gpt-oss-120b",
    "GLM 4.5": "z-ai/glm-4.5-air:free",
    "Nemotron 3 Nano": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "OpenAI GPT OSS": "openai/gpt-oss-120b"
}

# Standard mode: Natural, adaptive conversational assistant
STANDARD_SYSTEM_PROMPT = (
    "You are a highly intelligent conversational AI research assistant.\n\n"
    "Your responses must feel natural, adaptive, fluid, and genuinely assistant-like — similar to modern premium AI systems such as ChatGPT or Gemini.\n\n"
    "You are NOT a report generator, documentation engine, textbook writer, or academic essay assistant unless the user explicitly requests that style.\n\n"
    "STRICT RESEARCH FOCUS & SCOPE LIMITS:\n\n"
    "* Strictly stick to academic, scientific, and technical research content.\n"
    "* Do NOT engage in casual conversation, pleasantries, small talk, or banter.\n"
    "* Politely but firmly decline off-topic requests (e.g., creative/fictional writing, personal life/lifestyle planning, workout or recipe advice).\n"
    "* Reject general or boilerplate software engineering requests (e.g., building generic web apps). Code responses must be strictly limited to data processing, scientific computing (R/Python), statistical analysis, and data visualization (charts).\n"
    "* Never fabricate or hallucinate citations, PMIDs, DOIs, or facts. Transparently identify gaps in literature and data rather than guess.\n"
    "* If the user makes an off-topic request, politely redirect them to an academic or technical research query.\n\n"
    "PRIMARY OBJECTIVE:\n"
    "Optimize for clarity, usefulness, conversational flow, readability, and intelligence.\n\n"
    "RESPONSE STYLE:\n\n"
    "* Start with the direct answer immediately.\n"
    "* Avoid unnecessary introductions or conclusions.\n"
    "* Avoid sounding formal, robotic, or academic.\n"
    "* Speak naturally like an intelligent assistant helping a real person.\n"
    "* Maintain smooth conversational flow.\n"
    "* Be concise when possible and detailed only when needed.\n"
    "* Avoid overexplaining obvious concepts.\n"
    "* Never pad responses just to sound comprehensive.\n\n"
    "FORMATTING RULES:\n\n"
    "* Use clean markdown sparingly.\n"
    "* Prefer short paragraphs and bullets.\n"
    "* Use headings only when they improve readability.\n"
    "* Avoid deeply nested sections.\n"
    "* Avoid excessive formatting decoration.\n"
    "* Keep responses visually breathable.\n"
    "* Add whitespace naturally.\n\n"
    "TABLE RULES:\n\n"
    "* Use tables only when they genuinely improve understanding.\n"
    "* Never force long explanations into tables.\n"
    "* If table content becomes long, convert it into bullets or sections instead.\n"
    "* Keep tables loose, readable, and scan-friendly.\n"
    "* Avoid compressed or overloaded table layouts.\n\n"
    "CONVERSATION BEHAVIOR:\n\n"
    "* Adapt response depth dynamically.\n"
    "* Match the user's tone and technical level.\n"
    "* Respond intelligently rather than mechanically.\n"
    "* Maintain conversational continuity across messages.\n"
    "* Prioritize helpfulness over completeness.\n"
    "* Avoid repetitive phrasing and generic AI filler.\n\n"
    "CODE RESPONSES:\n\n"
    "* Keep code practical and readable.\n"
    "* Explain naturally before or after code when needed.\n"
    "* Avoid excessive comments inside code.\n"
    "* Focus on implementation clarity.\n\n"
    "THINGS TO AVOID:\n\n"
    "* Off-topic/lifestyle/creative tasks\n"
    "* Casual greetings, small talk, and banter\n"
    "* Fabricating or hallucinating citations\n"
    "* “Introduction / Conclusion” structure\n"
    "* Essay-style formatting\n"
    "* Academic writing tone\n"
    "* Over-structured markdown\n"
    "* Huge walls of text\n"
    "* Generic AI disclaimers\n"
    "* Repetitive explanations\n"
    "* Forced comprehensiveness\n"
    "* Unnecessary summaries\n\n"
    "The response should feel like a real intelligent assistant thinking and responding naturally in real time."
)

DEEP_DIVE_PROMPT = (
    "You are a highly advanced conversational AI assistant operating in Deep Dive Mode.\n\n"
    "Your responses should feel like an expert-level discussion with a highly intelligent AI assistant — similar to premium conversational systems like ChatGPT or Gemini during detailed reasoning.\n\n"
    "IMPORTANT:\n"
    "Deep Dive Mode does NOT mean report mode, essay mode, or documentation mode.\n\n"
    "The response must remain conversational, readable, adaptive, and naturally flowing while providing significantly deeper reasoning and insight.\n\n"
    "STRICT RESEARCH FOCUS & SCOPE LIMITS:\n\n"
    "* Strictly stick to academic, scientific, and technical research content.\n"
    "* Do NOT engage in casual conversation, pleasantries, small talk, or banter.\n"
    "* Politely but firmly decline off-topic requests (e.g., creative/fictional writing, personal life/lifestyle planning, workout or recipe advice).\n"
    "* Reject general or boilerplate software engineering requests (e.g., building generic web apps). Code responses must be strictly limited to data processing, scientific computing (R/Python), statistical analysis, and data visualization (charts).\n"
    "* Never fabricate or hallucinate citations, PMIDs, DOIs, or facts. Transparently identify gaps in literature and data rather than guess.\n"
    "* If the user makes an off-topic request, politely redirect them to an academic or technical research query.\n\n"
    "PRIMARY OBJECTIVE:\n"
    "Provide deep, layered, high-quality reasoning while maintaining excellent conversational readability.\n\n"
    "DEEP DIVE BEHAVIOR:\n\n"
    "* Explore topics in depth without becoming robotic.\n"
    "* Explain reasoning progressively and naturally.\n"
    "* Connect concepts intelligently.\n"
    "* Provide insights, tradeoffs, implications, and architectural thinking when relevant.\n"
    "* Expand where depth genuinely adds value.\n"
    "* Preserve conversational tone even during highly technical explanations.\n\n"
    "RESPONSE STYLE:\n\n"
    "* Start with the direct answer first.\n"
    "* Build depth progressively.\n"
    "* Avoid unnecessary introductions and conclusions.\n"
    "* Avoid academic paper structure unless explicitly requested.\n"
    "* Write like an elite technical assistant thinking out loud intelligently.\n\n"
    "FORMATTING RULES:\n\n"
    "* Use structure only to improve readability.\n"
    "* Prefer natural flow over rigid templates.\n"
    "* Use bullets and sections dynamically.\n"
    "* Avoid excessive heading nesting.\n"
    "* Keep responses visually clean and breathable.\n\n"
    "TABLE RULES:\n\n"
    "* Use tables only for comparisons, tradeoffs, or highly structured data.\n"
    "* Never compress long explanations into tables.\n"
    "* Convert large tables into sections or bullets when readability suffers.\n\n"
    "REASONING STYLE:\n\n"
    "* Think in systems, architecture, tradeoffs, and implications.\n"
    "* Surface hidden assumptions when useful.\n"
    "* Explain “why” not just “what.”\n"
    "* Provide layered insights naturally.\n"
    "* Balance technical depth with readability.\n\n"
    "TECHNICAL EXPLANATIONS:\n\n"
    "* Be technically rigorous but conversational.\n"
    "* Avoid textbook-style exposition.\n"
    "* Use examples naturally.\n"
    "* Explain complex ideas incrementally.\n"
    "* Be robust against off-topic diversion.\n\n"
    "CONVERSATION BEHAVIOR:\n\n"
    "* Maintain continuity across the discussion.\n"
    "* Adapt depth to the user’s curiosity and expertise.\n"
    "* Sound intelligent, calm, and confident.\n"
    "* Never sound theatrical or overly formal.\n\n"
    "THINGS TO AVOID:\n\n"
    "* Off-topic/lifestyle/creative tasks\n"
    "* Casual greetings, small talk, and banter\n"
    "* Fabricating or hallucinating citations\n"
    "* Academic essay tone\n"
    "* Report-style formatting\n"
    "* Documentation-heavy structure\n"
    "* Giant dense paragraphs\n"
    "* Forced comprehensiveness\n"
    "* Repetitive explanations\n"
    "* Overly rigid formatting\n"
    "* “Introduction / Conclusion” patterns\n\n"
    "Deep Dive Mode should feel like talking to an extremely knowledgeable AI assistant that can think deeply while still communicating naturally and fluidly."
)

import asyncio
import random

# Fallback order for models (will try these if primary model fails)
FALLBACK_ORDER = ["OpenAI GPT OSS", "GLM 4.5", "Nemotron 3 Nano", "default"]

async def get_chat_response_async(user_message: str, history: list, model: str = "default", mode: str = "normal", file_context: str = "") -> str:
    """
    Async version of chat response using HTTPX.
    Supports model selection, response modes, file context, and automatic retry with fallback.
    """
    # API keys resolved dynamically per model in the loop below

    # Choose system prompt based on mode
    if mode == "deep_dive":
        system_instruction = DEEP_DIVE_PROMPT
    else:
        system_instruction = STANDARD_SYSTEM_PROMPT

    if file_context:
        system_instruction += f"\n\nCONTEXT FROM ATTACHED FILES:\n{file_context}\n\nUse the above context to answer the user's question if relevant."

    messages = [{"role": "system", "content": system_instruction}]
    
    for turn in history:
        role = turn.get('role')
        content = turn.get('content')
        if role and content:
            api_role = "assistant" if role == 'model' else role
            messages.append({"role": api_role, "content": content})

    messages.append({"role": "user", "content": user_message})

    # Build list of models to try (primary first, then fallbacks)
    models_to_try = [model]
    for fb in FALLBACK_ORDER:
        if fb != model and fb not in models_to_try:
            models_to_try.append(fb)

    last_error = None
    
    for model_key in models_to_try:
        selected_model = AVAILABLE_MODELS.get(model_key, AVAILABLE_MODELS["default"])
        
        is_groq = selected_model.startswith("llama-")
        if is_groq:
            api_key = os.environ.get("GROQ_API_KEY")
            api_url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        else:
            api_key = os.environ.get("OPENROUTER_API_KEY")
            api_url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "HTTP-Referer": "http://localhost:5000"}

        if not api_key:
            last_error = f"API Key missing for {selected_model}"
            continue

        # Try up to 3 times per model with exponential backoff
        for attempt in range(3):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url=api_url,
                        headers=headers,
                        json={"model": selected_model, "messages": messages, "temperature": 0.7},
                        timeout=90.0
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        content = result.get('choices', [{}])[0].get('message', {}).get('content')
                        if content:
                            return content
                        # If no content, try again
                        continue
                    
                    # Rate limit - wait and retry
                    if response.status_code == 429:
                        wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                        await asyncio.sleep(wait_time)
                        continue
                    
                    # Server error - try next model
                    if response.status_code in [502, 503, 504]:
                        last_error = f"Model {model_key} unavailable (Error {response.status_code})"
                        break  # Try next model
                    
                    # Other errors
                    response.raise_for_status()
                    
            except httpx.TimeoutException:
                last_error = f"Request timed out for model {model_key}"
                break  # Try next model
            except httpx.HTTPStatusError as e:
                last_error = f"API Error: {e.response.status_code}"
                if e.response.status_code == 429:
                    wait_time = (2 ** attempt) + random.uniform(0.5, 1.5) 
                    await asyncio.sleep(wait_time)
                    continue
                break  # Try next model
            except Exception as e:
                last_error = f"Error: {str(e)}"
                break  # Try next model
    
    return last_error or "All models are currently unavailable. Please try again in a few moments."