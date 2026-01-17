"""Provider registry and factory."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from ralph.providers.base import BaseProvider
from ralph.providers.codex import CodexProvider
from ralph.providers.claude import ClaudeProvider
from ralph.providers.cursor import CursorProvider
from ralph.providers.gemini import GeminiProvider
from ralph.providers.rotation import ProviderRotation

PROVIDERS = {
    "agent": CursorProvider,
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
    "codex": CodexProvider,
}


def get_provider(name: str) -> BaseProvider:
    """Get provider instance by name."""
    provider_class = PROVIDERS.get(name)
    if not provider_class:
        raise ValueError(f"Unknown provider: {name}")
    return provider_class()


def detect_available_providers() -> list[BaseProvider]:
    """Detect which providers are available on system.
    
    Returns list of provider instances in rotation order.
    """
    available = []
    for name, provider_class in PROVIDERS.items():
        provider = provider_class()
        if provider.is_available():
            available.append(provider)
    return available


def get_provider_rotation() -> ProviderRotation:
    """Get provider rotation manager with all available providers."""
    providers = detect_available_providers()
    return ProviderRotation(providers)
