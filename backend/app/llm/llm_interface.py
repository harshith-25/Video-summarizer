from abc import ABC, abstractmethod
from typing import List, Dict, Any

class LLMInterface(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        pass
    
    @abstractmethod
    def generate_streaming(self, prompt: str, system_prompt: str = None, **kwargs):
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        pass
