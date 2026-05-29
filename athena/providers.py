"""
Providers - Multi-provider LLM support for Athena
Supports OpenAI, DeepSeek, Moonshot, Xiaomi, GLM, and more.
"""
import os
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


def load_env_file(env_path: str = "~/.athena/.env"):
    """Load .env file if exists."""
    path = Path(env_path).expanduser()
    if path.exists():
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value:
                        os.environ.setdefault(key, value)


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    name: str
    api_url: str
    api_key: Optional[str] = None
    model: str = "default"
    temperature: float = 0.7
    max_tokens: int = 4096
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
    
    @property
    def name(self) -> str:
        return self.config.name


class OpenAICompatibleProvider(Provider):
    """Provider using OpenAI-compatible API format."""
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        import httpx
        
        try:
            headers = {"Content-Type": "application/json"}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.post(
                    f"{self.config.api_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": self.config.model,
                        "messages": messages,
                        "temperature": self.config.temperature,
                        "max_tokens": self.config.max_tokens,
                        **kwargs,
                    }
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"{self.config.name} error: {e}")
    
    def is_available(self) -> bool:
        import httpx
        try:
            headers = {}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            with httpx.Client(timeout=5) as client:
                # Just check if API responds
                response = client.get(
                    f"{self.config.api_url}/models",
                    headers=headers
                )
                return response.status_code in (200, 401)  # 401 means key needed but API exists
        except Exception:
            return False


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
            raise ConnectionError("Cannot connect to Ollama. Is it running? (ollama serve)")
        except Exception as e:
            raise RuntimeError(f"Ollama error: {e}")
    
    def is_available(self) -> bool:
        import httpx
        try:
            with httpx.Client(timeout=3) as client:
                response = client.get(f"{self.config.api_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False


class ProviderRegistry:
    """
    Registry for LLM providers.
    
    Example:
        >>> registry = ProviderRegistry()
        >>> registry.auto_configure()  # Auto-detect available providers
        >>> provider = registry.get_best()
        >>> response = provider.chat([{"role": "user", "content": "Hello"}])
    """
    
    def __init__(self):
        self.providers: Dict[str, Provider] = {}
        self._default: Optional[str] = None
    
    def register(self, name: str, provider: Provider):
        """Register a provider."""
        self.providers[name] = provider
        logger.info(f"Registered provider: {name}")
    
    def get(self, name: str) -> Optional[Provider]:
        """Get a provider by name."""
        return self.providers.get(name)
    
    def get_best(self) -> Optional[Provider]:
        """Get the best available provider."""
        # Priority order for Chinese users
        priority = [
            "xiaomi", "deepseek", "moonshot", "glm",
            "openai", "openrouter", "nvidia", "ollama"
        ]
        
        # Try priority order first
        for name in priority:
            provider = self.providers.get(name)
            if provider and provider.is_available():
                return provider
        
        # Fall back to any available
        for provider in self.providers.values():
            if provider.is_available():
                return provider
        
        return None
    
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
    
    def auto_configure(self):
        """Auto-configure providers based on available API keys."""
        # Load .env file
        load_env_file()
        load_env_file("~/.env")
        
        # Ollama (local)
        self.register("ollama", OllamaProvider(ProviderConfig(
            name="ollama",
            api_url="http://localhost:11434",
            model="llama3.2:3b",
        )))
        
        # Xiaomi (MiMo)
        xiaomi_key = os.environ.get("XIAOMI_API_KEY")
        if xiaomi_key:
            self.register("xiaomi", OpenAICompatibleProvider(ProviderConfig(
                name="xiaomi",
                api_url="https://token-plan-cn.xiaomimimo.com/v1",
                api_key=xiaomi_key,
                model="mimo-v2.5",
                max_tokens=4096,
            )))
        
        # DeepSeek
        deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
        if deepseek_key:
            self.register("deepseek", OpenAICompatibleProvider(ProviderConfig(
                name="deepseek",
                api_url="https://api.deepseek.com",
                api_key=deepseek_key,
                model="deepseek-chat",
                max_tokens=8192,
            )))
        
        # Moonshot (Kimi)
        moonshot_key = os.environ.get("MOONSHOT_API_KEY")
        if moonshot_key:
            self.register("moonshot", OpenAICompatibleProvider(ProviderConfig(
                name="moonshot",
                api_url="https://api.moonshot.cn/v1",
                api_key=moonshot_key,
                model="moonshot-v1-8k",
                max_tokens=4096,
            )))
        
        # GLM (Zhipu)
        glm_key = os.environ.get("GLM_CODING_API_KEY")
        if glm_key:
            self.register("glm", OpenAICompatibleProvider(ProviderConfig(
                name="glm",
                api_url="https://open.bigmodel.cn/api/paas/v4",
                api_key=glm_key,
                model="glm-4-flash",
                max_tokens=4096,
            )))
        
        # OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            self.register("openai", OpenAICompatibleProvider(ProviderConfig(
                name="openai",
                api_url="https://api.openai.com/v1",
                api_key=openai_key,
                model="gpt-4o-mini",
                max_tokens=4096,
            )))
        
        # OpenRouter
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        if openrouter_key:
            self.register("openrouter", OpenAICompatibleProvider(ProviderConfig(
                name="openrouter",
                api_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key,
                model="anthropic/claude-3-haiku",
                max_tokens=4096,
            )))
        
        # NVIDIA
        nvidia_key = os.environ.get("NVIDIA_API_KEY")
        if nvidia_key:
            self.register("nvidia", OpenAICompatibleProvider(ProviderConfig(
                name="nvidia",
                api_url="https://integrate.api.nvidia.com/v1",
                api_key=nvidia_key,
                model="meta/llama-3.3-70b-instruct",
                max_tokens=4096,
            )))
        
        # Google
        google_key = os.environ.get("GOOGLE_API_KEY")
        if google_key:
            self.register("google", OpenAICompatibleProvider(ProviderConfig(
                name="google",
                api_url="https://generativelanguage.googleapis.com/v1beta/openai",
                api_key=google_key,
                model="gemini-2.5-flash",
                max_tokens=4096,
            )))
        
        logger.info(f"Auto-configured {len(self.providers)} providers")


def create_default_registry() -> ProviderRegistry:
    """Create and auto-configure a provider registry."""
    registry = ProviderRegistry()
    registry.auto_configure()
    return registry
