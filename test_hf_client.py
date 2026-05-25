import os
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# Load env variables on the host
load_dotenv(dotenv_path="/home/mohammed/ScholarForge/.env")

token = os.environ.get("HF_TOKEN")
if token:
    token = token.strip('"').strip("'")

print(f"Loaded HF_TOKEN starting with: {token[:8] if token else 'None'}")

client = InferenceClient(api_key=token)

models = [
    "zai-org/GLM-5.1",
    "Qwen/Qwen3-0.6B",
    "meta-llama/Llama-3.1-8B-Instruct"
]

for model_id in models:
    print(f"\n--- Testing text_generation for {model_id} ---")
    try:
        response = client.text_generation(
            prompt="Hello! Give me a 1-sentence greeting.",
            model=model_id,
            max_new_tokens=50,
            temperature=0.7
        )
        print("Success! Response:")
        print(response)
    except Exception as e:
        print(f"Failed: {e}")
