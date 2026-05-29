"""
Providers - Multi-provider LLM support for Athena
Supports Ollama, OpenAI, DeepSeek, and more.
"""
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    name: str
    api_url: str
    api_key: Optional[str] = None
    model: str = "default"
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 120


class Provider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
    
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Send chat messages and get response."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass


class OllamaProvider(Provider):
    """Ollama local LLM provider."""
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        import httpx
        
        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.post(
                    f"{self.config.api_url}/api/chat",
                    json={
                        "model": self.config.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": self.config.temperature,
                            "num_predict": self.config.max_tokens,
                        }
                    }
                )
                response.raise_for_status()
                return response.json()["message"]["content"]
        except httpx.ConnectError:
            raise ConnectionError("Cannot connect to Ollama. Is it running?")
        except Exception as e:
            raise RuntimeError(f"Ollama error: {e}")
    
    def is_available(self) -> bool:
        import httpx
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.config.api_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False


class OpenAIProvider(Provider):
    """OpenAI API provider."""
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        import httpx
        
        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.config.model,
                        "messages": messages,
                        "temperature": self.config.temperature,
                        "max_tokens": self.config.max_tokens,
                    }
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"OpenAI error: {e}")
    
    def is_available(self) -> bool:
        return bool(self.config.api_key)


class DeepSeekProvider(Provider):
    """DeepSeek API provider."""
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        import httpx
        
        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.config.model or "deepseek-chat",
                        "messages": messages,
                        "temperature": self.config.temperature,
                        "max_tokens": self.config.max_tokens,
                    }
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"DeepSeek error: {e}")
    
    def is_available(self) -> bool:
        return bool(self.config.api_key)


class MoonshotProvider(Provider):
    """Moonshot (Kimi) API provider."""
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        import httpx
        
        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.post(
                    "https://api.moonshot.cn/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.config.model or "moonshot-v1-8k",
                        "messages": messages,
                        "temperature": self.config.temperature,
                    }
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Moonshot error: {e}")
    
    def is_available(self) -> bool:
        return bool(self.config.api_key)


class ProviderRegistry:
    """
    Registry for LLM providers.
    
    Example:
        >>> registry = ProviderRegistry()
        >>> registry.register("ollama", OllamaProvider, {"api_url": "http://localhost:11434"})
        >>> provider = registry.get("ollama")
        >>> response = provider.chat([{"role": "user", "content": "Hello"}])
    """
    
    def __init__(self):
        self.providers: Dict[str, Provider] = {}
        self._configs: Dict[str, ProviderConfig] = {}
    
    def register(self, name: str, provider_class: type, config: Dict[str, Any]):
        """Register a provider."""
        provider_config = ProviderConfig(
            name=name,
            **config
        )
        self._configs[name] = provider_config
        self.providers[name] = provider_class(provider_config)
        logger.info(f"Registered provider: {name}")
    
    def get(self, name: str) -> Optional[Provider]:
        """Get a provider by name."""
        return self.providers.get(name)
    
    def list_providers(self) -> Dict[str, bool]:
        """List all providers and their availability."""
        return {
            name: provider.is_available()
            for name, provider in self.providers.items()
        }
    
    def set_default(self, name: str):
        """Set the default provider."""
        if name in self.providers:
            self._default = name
        else:
            raise ValueError(f"Provider '{name}' not registered")
    
    def get_default(self) -> Optional[Provider]:
        """Get the default provider."""
        default_name = getattr(self, '_default', None)
        if default_name:
            return self.providers.get(default_name)
        # Return first available
        for provider in self.providers.values():
            if provider.is_available():
                return provider
        return None


def create_default_registry() -> ProviderRegistry:
    """Create a provider registry with default providers."""
    registry = ProviderRegistry()
    
    # Ollama (local)
    registry.register("ollama", OllamaProvider, {
        "api_url": "http://localhost:11434",
        "model": "llama3.2:3b",
    })
    
    # OpenAI (if key available)
    import os
    if os.environ.get("OPENAI_API_KEY"):
        registry.register("openai", OpenAIProvider, {
            "api_key": os.environ["OPENAI_API_KEY"],
            "model": "gpt-4o-mini",
        })
    
    # DeepSeek (if key available)
    if os.environ.get("DEEPSEEK_API_KEY"):
        registry.register("deepseek", DeepSeekProvider, {
            "api_key": os.environ["DEEPSEEK_API_KEY"],
            "model": "deepseek-chat",
        })
    
    # Moonshot (if key available)
    if os.environ.get("MOONSHOT_API_KEY"):
        registry.register("moonshot", MoonshotProvider, {
            "api_key": os.environ["MOONSHOT_API_KEY"],
            "model": "moonshot-v1-8k",
        })
    
    return registry
