import os
import requests
import json
import logging
import time
from typing import List, Dict, Any, Generator
from app.llm.llm_interface import LLMInterface

logger = logging.getLogger("app")

class MistralProvider(LLMInterface):
    def __init__(self):
        self.api_url = os.getenv("MISTRAL_CLOUD_API_URL", "https://api.mistral.ai/v1/chat/completions")
        self.api_key = os.getenv("MISTRAL_CLOUD_API_KEY")
        self.model = os.getenv("MISTRAL_CLOUD_MODEL", "mistral-medium-latest")
        
        if not self.api_key:
            logger.warning("[MistralProvider] MISTRAL_CLOUD_API_KEY is not configured in .env")
        else:
            logger.info(f"[MistralProvider] Initialized targeting Model: {self.model} at {self.api_url}")

    def generate(self, prompt: str, system_prompt: str = None, return_tokens=False, **kwargs) -> Any:
        if not self.api_key:
            raise ValueError("Mistral Cloud API key is missing.")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2000)
        }
        
        start_time = time.time()
        try:
            logger.info(f"[MistralProvider] Sending POST request to {self.api_url}")
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            res_data = response.json()
            content = res_data["choices"][0]["message"]["content"]
            duration = time.time() - start_time
            
            usage = res_data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            
            logger.info(
                f"Mistral API success: prompt_tokens={prompt_tokens}, completion_tokens={completion_tokens}, "
                f"total_tokens={total_tokens}, duration={duration:.2f}s"
            )
            
            if return_tokens:
                token_stats = {
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': total_tokens,
                    'model_name': self.model,
                    'provider': 'Mistral Cloud',
                    'duration': duration
                }
                return content, token_stats
                
            return content
            
        except Exception as e:
            logger.error(f"[MistralProvider] Request failed: {e}", exc_info=True)
            raise RuntimeError(f"Mistral API Request failed: {e}")

    def generate_streaming(self, prompt: str, system_prompt: str = None, **kwargs) -> Generator[str, None, None]:
        if not self.api_key:
            raise ValueError("Mistral Cloud API key is missing.")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2000)
        }
        
        try:
            logger.info(f"[MistralProvider] Initiating SSE stream from {self.api_url}")
            response = requests.post(self.api_url, json=payload, headers=headers, stream=True, timeout=60)
            response.raise_for_status()
            
            for raw in response.iter_lines():
                if not raw:
                    continue
                line = raw.decode("utf-8")
                
                # SSE pings check
                if line.startswith(":"):
                    continue
                    
                if not line.startswith("data:"):
                    continue
                    
                content = line[len("data: "):].strip()
                if content == "[DONE]":
                    break
                    
                data = json.loads(content)
                choices = data.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        yield token
                        
        except Exception as e:
            logger.error(f"[MistralProvider] SSE stream failed: {e}", exc_info=True)
            raise RuntimeError(f"Mistral Streaming failed: {e}")

    def count_tokens(self, text: str) -> int:
        # Standard token approximation for Mistral (approx. 4 chars per token)
        return len(text) // 4