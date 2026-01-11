"""Minimal vision_cortex package shims used for local development and tests.

This package provides lightweight implementations of the interfaces referenced
by omni_gateway so the app can start and the headless-team endpoints work.
These are intentionally small and safe; replace with full implementations
from the main project when available.
"""

__all__ = [
    "agents",
    "integration",
    "instrumentation",
]
