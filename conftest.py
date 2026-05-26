import pytest

# Makes asyncio tests work without per-test decorator overhead
pytest_plugins = ["pytest_asyncio"]