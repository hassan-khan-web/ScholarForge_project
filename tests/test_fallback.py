import os
import pytest
from unittest.mock import MagicMock, patch
import httpx

from backend import AI_engine

def test_get_fallback_chain():
    # Test GLM-5.1 prioritizes other HF models, then Groq, then OpenRouter
    chain = AI_engine.get_fallback_chain("zai-org/GLM-5.1")
    assert chain[0] == "zai-org/GLM-5.1"
    assert "Qwen/Qwen3-0.6B" in chain
    assert "meta-llama/Llama-3.1-8B-Instruct" in chain
    assert "llama-3.3-70b-versatile" in chain
    assert "openai/gpt-oss-120b" in chain
    
    # Test Groq prioritizes Groq, then HF, then OpenRouter
    chain_groq = AI_engine.get_fallback_chain("llama-3.3-70b-versatile")
    assert chain_groq[0] == "llama-3.3-70b-versatile"
    assert chain_groq[1] == "llama-3.1-8b-instant"
    assert "zai-org/GLM-5.1" in chain_groq
    assert "openai/gpt-oss-120b" in chain_groq

@patch("httpx.Client.post")
def test_call_llm_success_first_try(mock_post):
    # Mock successful response on first call
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": "This is generated text by GLM"
            }
        }]
    }
    mock_post.return_value = mock_response
    
    # Set env vars so validation passes
    with patch.dict(os.environ, {"HF_TOKEN": "test_token"}):
        result = AI_engine.call_llm("zai-org/GLM-5.1", "system", "user")
        assert result == "This is generated text by GLM"
        assert mock_post.call_count == 1
        
        # Verify it passed the right model and token
        called_args, called_kwargs = mock_post.call_args
        assert called_kwargs["json"]["model"] == "zai-org/GLM-5.1"
        assert called_kwargs["headers"]["Authorization"] == "Bearer test_token"

@patch("httpx.Client.post")
def test_call_llm_fallback_sequence(mock_post):
    # Setup responses: first fails with 403 (e.g. permission error), second succeeds
    response_fail = MagicMock()
    response_fail.status_code = 403
    response_fail.text = "Forbidden - No provider permissions"
    
    response_success = MagicMock()
    response_success.status_code = 200
    response_success.json.return_value = {
        "choices": [{
            "message": {
                "content": "Succeeded on Qwen"
            }
        }]
    }
    
    # side_effect returns first fail, then success
    mock_post.side_effect = [response_fail, response_success]
    
    with patch.dict(os.environ, {"HF_TOKEN": "test_token"}):
        result = AI_engine.call_llm("zai-org/GLM-5.1", "system", "user")
        assert result == "Succeeded on Qwen"
        assert mock_post.call_count == 2
        
        # The second call model should be the next HF model in chain
        first_call = mock_post.call_args_list[0]
        second_call = mock_post.call_args_list[1]
        assert first_call[1]["json"]["model"] == "zai-org/GLM-5.1"
        assert second_call[1]["json"]["model"] == "Qwen/Qwen3-0.6B"

@patch("httpx.Client.post")
def test_call_llm_all_failed(mock_post):
    # Setup responses: all fail
    response_fail = MagicMock()
    response_fail.status_code = 403
    response_fail.text = "Forbidden"
    mock_post.return_value = response_fail
    
    # Patch all tokens so they exist
    env_patch = {
        "HF_TOKEN": "test_hf",
        "GROQ_API_KEY": "test_groq",
        "OPENROUTER_API_KEY": "test_or"
    }
    
    with patch.dict(os.environ, env_patch), patch("time.sleep", return_value=None):
        result = AI_engine.call_llm("zai-org/GLM-5.1", "system", "Target section user query context")
        
        # Check that we got the formatted fallback block
        assert "[Critical Connection Error: Model Generation Failed]" in result
        assert "Target section user query context" in result
        assert "zai-org/GLM-5.1 failed" in result
        assert "llama-3.3-70b-versatile failed" in result
