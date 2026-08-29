"""
Gemini API Key Manager
======================
Reads multiple Gemini API keys from environment variables, tests them at
startup, and provides round-robin selection of working keys.

Environment variable format:
  GEMINI_API_KEY=key1,key2,key3
  -- or single key: GEMINI_API_KEY=key1

Keys are tested by calling the Gemini API listModels endpoint. Only keys
that return a successful response are kept in the rotation pool.
"""

import os
import asyncio
import itertools
import threading
import logging
import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
GEMINI_TEST_MODEL = "gemini-2.0-flash"  # lightweight model to test with


class GeminiKeyManager:
    """Thread-safe, round-robin Gemini API key manager."""

    def __init__(self):
        self._keys: list[str] = []
        self._working_keys: list[str] = []
        self._cycle: itertools.cycle | None = None
        self._lock = threading.Lock()
        self._initialized = False
        self._test_results: dict[str, bool] = {}

    def load_keys(self) -> list[str]:
        """Parse Gemini API keys from environment. Supports comma-separated."""
        raw = os.environ.get(GEMINI_API_KEY_ENV, "").strip()
        if not raw:
            return []
        # Split on commas, strip whitespace, filter empty
        keys = [k.strip() for k in raw.split(",") if k.strip()]
        with self._lock:
            self._keys = keys
        logger.info(f"Loaded {len(keys)} Gemini API key(s) from {GEMINI_API_KEY_ENV}")
        return keys

    async def _test_key(self, key: str) -> bool:
        """Test a Gemini API key by calling listModels."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://generativelanguage.googleapis.com/v1beta/models",
                    headers={"x-goog-api-key": key},
                )
                if resp.status_code == 200:
                    return True
                logger.warning(f"Gemini key ...{key[-6:]} returned status {resp.status_code}")
                return False
        except Exception as e:
            logger.warning(f"Gemini key ...{key[-6:]} test failed: {e}")
            return False

    async def initialize(self) -> None:
        """Test all loaded keys and build the working rotation pool."""
        if self._initialized:
            return

        keys = self.load_keys()
        if not keys:
            logger.warning("No Gemini API keys configured. AI features will be unavailable.")
            with self._lock:
                self._working_keys = []
                self._cycle = None
                self._initialized = True
            return

        logger.info(f"Testing {len(keys)} Gemini API key(s)...")
        tasks = [self._test_key(key) for key in keys]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        working = []
        for key, result in zip(keys, results):
            is_working = result is True
            self._test_results[key[-6:]] = is_working
            if is_working:
                working.append(key)
                logger.info(f"  ✓ Key ...{key[-6:]} is working")
            else:
                logger.warning(f"  ✗ Key ...{key[-6:]} is not working")

        with self._lock:
            self._working_keys = working
            if working:
                self._cycle = itertools.cycle(working)
            else:
                self._cycle = None
            self._initialized = True

        logger.info(
            f"Gemini key manager initialized: "
            f"{len(working)}/{len(keys)} key(s) working"
        )

    def get_key(self) -> str | None:
        """Get the next working API key using round-robin selection.

        Returns None if no keys are configured or all keys failed testing.
        """
        with self._lock:
            if not self._cycle or not self._working_keys:
                return None
            return next(self._cycle)

    def get_status(self) -> dict:
        """Return the current status of the key manager."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_keys": len(self._keys),
                "working_keys": len(self._working_keys),
                "key_status": {
                    f"...{k[-6:]}": "working" if k in self._working_keys else "failed"
                    for k in self._keys
                },
            }

    def mark_key_failed(self, key: str) -> None:
        """Mark a key as failed (e.g., after a 429 or 403 response).

        The key is removed from the rotation pool but not deleted.
        """
        with self._lock:
            if key in self._working_keys:
                self._working_keys.remove(key)
                if self._working_keys:
                    self._cycle = itertools.cycle(self._working_keys)
                else:
                    self._cycle = None
                logger.warning(
                    f"Key ...{key[-6:]} removed from rotation "
                    f"({len(self._working_keys)} keys remaining)"
                )


# Singleton instance
_key_manager = GeminiKeyManager()


def get_key_manager() -> GeminiKeyManager:
    """Get the singleton Gemini key manager instance."""
    return _key_manager


async def initialize_key_manager() -> None:
    """Initialize the key manager at application startup."""
    await _key_manager.initialize()


def get_gemini_api_key() -> str | None:
    """Get the next available Gemini API key. Convenience function."""
    return _key_manager.get_key()
