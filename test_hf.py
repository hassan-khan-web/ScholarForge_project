import os
import httpx
from dotenv import load_dotenv

# Load env variables on the host
load_dotenv(dotenv_path="/home/mohammed/ScholarForge/.env")

token = os.environ.get("HF_TOKEN")
if token:
    token = token.strip('"').strip("'")

print(f"Loaded HF_TOKEN starting with: {token[:8] if token else 'None'}")

models = [
    "zai-org/GLM-5.1",
    "Qwen/Qwen3-0.6B",
    "meta-llama/Llama-3.1-8B-Instruct"
]

def test_hf_inference_provider_completions(model_id):
    # Testing the OpenAI-compatible route under hf-inference provider
    url = f"https://router.huggingface.co/hf-inference/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_id,
        "messages": [
            {"role": "user", "content": "Hello! Give me a 1-sentence greeting."}
        ],
        "max_tokens": 50,
        "temperature": 0.7
    }
    
    print(f"\n--- Testing hf-inference/v1/chat/completions for {model_id} ---")
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                res_json = response.json()
                print("Success! Response:")
                print(res_json["choices"][0]["message"]["content"])
                return True
            else:
                print(f"Failed with response: {response.text[:200]}")
                return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_hf_inference_provider_model_direct(model_id):
    # Testing direct model endpoint under hf-inference provider
    url = f"https://router.huggingface.co/hf-inference/models/{model_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": "Hello! Give me a 1-sentence greeting.",
        "parameters": {
            "max_new_tokens": 50,
            "temperature": 0.7
        }
    }
    
    print(f"\n--- Testing hf-inference/models/ direct for {model_id} ---")
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("Success! Response:")
                print(response.json())
                return True
            else:
                print(f"Failed with response: {response.text[:200]}")
                return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

for model in models:
    if not test_hf_inference_provider_completions(model):
        test_hf_inference_provider_model_direct(model)
