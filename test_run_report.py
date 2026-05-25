import os
import sys
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.getcwd())

load_dotenv()

# We'll use the docker container context to run this to ensure database and Redis are reachable
# Let's import the engine
from backend import AI_engine

print("Running manual verification of the report generation pipeline...")
print("Target model: zai-org/GLM-5.1")
print("Expected behavior: GLM-5.1, Qwen3, and Llama 3.1 8B Instruct will fail due to 403 permissions, then fall back to Groq Llama 3.3 70B and succeed.")

try:
    search_context, report, chart_path = AI_engine.run_ai_engine_with_return(
        query="Impact of AI on Healthcare",
        user_format="literature_review",
        page_count=2, # Short for fast test
        file_data_list=None,
        task=None,
        use_council=False,
        model="zai-org/GLM-5.1"
    )
    
    print("\n================== PIPELINE RUN RESULTS ==================")
    print(f"Chart generated at: {chart_path}")
    print(f"Report length: {len(report)} characters")
    print(f"Contains fallback error notice: {'[Critical Connection Error' in report}")
    print("\nFirst 500 characters of the report:")
    print("-" * 50)
    print(report[:500])
    print("-" * 50)
    print("\nSUCCESS: Manual report generation verification complete.")
except Exception as e:
    print(f"\nFAILURE: Run crashed with exception: {e}")
    sys.exit(1)
