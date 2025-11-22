import os
import requests
import json

# ---
# --- THIS IS THE FIX ---
# ---
# We will use a fast, free, chat-optimized model from OpenRouter
LLAMA_MODEL_STRING = "nvidia/nemotron-nano-12b-v2-vl:free" 
# ---
# ---


def get_chat_response(user_message: str, history: list) -> str:
    """
    Gets a conversational response from the AI using the OpenRouter API.
    'history' is a list of previous turns in the chat.
    """
    try:
        # --- UPDATED ---
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return "Error: OPENROUTER_API_KEY environment variable not set."

        system_instruction = (
            "You are a helpful AI research assistant. "
            "Answer the user's questions clearly and concisely. "
            "You do not have access to live internet data unless it is provided to you."
        )

        messages = [{"role": "system", "content": system_instruction}]
        
        for turn in history:
            role = turn.get('role')
            content = turn.get('content')
            
            if role and content:
                if role == 'model':
                    messages.append({"role": "assistant", "content": content})
                else:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_message})

        response = requests.post(
            # --- UPDATED ---
            url="https://openrouter.ai/api/v1/chat/completions", 
            headers={
                # --- UPDATED ---
                "Authorization": f"Bearer {api_key}", 
                "Content-Type": "application/json"
            },
            data=json.dumps({
                # --- UPDATED ---
                "model": LLAMA_MODEL_STRING, 
                "messages": messages,
                "temperature": 0.7
            })
        )
        
        response.raise_for_status() 

        result = response.json()
        
        ai_content = result['choices'][0]['message']['content']
        
        return ai_content or "No response from AI."

    except requests.exceptions.HTTPError as e:
        # --- UPDATED ---
        return f"OpenRouter API Error: {e.response.status_code} {e.response.text}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"