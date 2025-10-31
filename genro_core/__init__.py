"""Genro Core - Core utilities and decorators for Genro framework."""

from .decorators import apiready
from .introspection import get_api_structure, get_api_structure_multi

__version__ = "0.1.0"

__all__ = ["apiready", "get_api_structure", "get_api_structure_multi"]
