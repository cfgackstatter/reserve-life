"""
LLM Client Module
Generic functionality for interacting with Large Language Models.
"""

from typing import Optional, Dict, Any, List
import os
import json
import re
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import LLM dependencies
try:
    import httpx
    from perplexity import Perplexity  # type: ignore
    PERPLEXITY_AVAILABLE = True
except ImportError:
    PERPLEXITY_AVAILABLE = False
    httpx = None
    Perplexity = None


@lru_cache(maxsize=1)
def get_perplexity_client():
    """
    Create and cache a Perplexity API client.
    
    Returns:
        Perplexity client instance or None if not available
    """
    if not PERPLEXITY_AVAILABLE or not httpx or not Perplexity:
        print("❌ Perplexity library not available")
        return None
    
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        print("❌ PERPLEXITY_API_KEY not found in environment")
        return None
    
    try:
        timeout_config = httpx.Timeout(connect=5.0, read=20.0, write=5.0, pool=5.0)
        client = Perplexity(api_key=api_key, timeout=timeout_config)
        print("✅ Perplexity client initialized")
        return client
    except Exception as e:
        print(f"❌ Error creating Perplexity client: {e}")
        return None


def query_llm(prompt: str, model: str = "sonar-pro", max_tokens: int = 150, temperature: float = 0.0) -> Optional[str]:
    """
    Send a query to the LLM and return the response.
    
    Args:
        prompt: Text prompt to send to the LLM
        model: Model name to use (default: "sonar-pro")
        max_tokens: Maximum tokens in response
        temperature: Randomness in response (0.0 = deterministic)
        
    Returns:
        LLM response as string, or None if failed
    """
    client = get_perplexity_client()
    if not client:
        return None
    
    try:
        print("🤖 Querying LLM...")
        
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        response = str(completion.choices[0].message.content or "").strip()
        print(f"✅ LLM responded with {len(response)} characters")
        return response
        
    except Exception as e:
        print(f"❌ LLM query failed: {e}")
        return None


def extract_json_from_response(response: str, required_keys: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """
    Extract and parse JSON from LLM response text.
    
    Args:
        response: Raw LLM response text
        required_keys: List of keys that must be present in parsed JSON
        
    Returns:
        Parsed JSON dictionary or None if parsing fails
    """
    if not response:
        return None
    
    # Try parsing the entire response as JSON first
    try:
        data = json.loads(response)
        if required_keys:
            if all(key in data for key in required_keys):
                return data
        else:
            return data
    except json.JSONDecodeError:
        pass
    
    # Fallback: Try to find JSON pattern in the text using regex
    json_pattern = r'\{[^{}]*\}'
    matches = re.findall(json_pattern, response)
    
    for match in matches:
        try:
            data = json.loads(match)
            if required_keys:
                if all(key in data for key in required_keys):
                    return data
            else:
                return data
        except json.JSONDecodeError:
            continue
    
    # Try more complex nested JSON
    nested_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
    matches = re.findall(nested_pattern, response)
    
    for match in matches:
        try:
            data = json.loads(match)
            if required_keys:
                if all(key in data for key in required_keys):
                    return data
            else:
                return data
        except json.JSONDecodeError:
            continue
    
    return None


def is_llm_available() -> bool:
    """
    Check if LLM functionality is available.
    
    Returns:
        True if LLM can be used, False otherwise
    """
    return PERPLEXITY_AVAILABLE and get_perplexity_client() is not None
