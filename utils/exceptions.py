"""
Custom exceptions for SuperCat Bot.
"""
from typing import Optional


class SuperCatError(Exception):
    """Base exception for SuperCat Bot."""
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class BotInitializationError(SuperCatError):
    """Raised when bot initialization fails."""
    pass


class WebhookError(SuperCatError):
    """Raised when webhook operations fail."""
    pass


class ConfigurationError(SuperCatError):
    """Raised when configuration is invalid."""
    pass


class HandlerError(SuperCatError):
    """Raised when handler operations fail."""
    pass
