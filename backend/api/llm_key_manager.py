from typing import List, Optional
import threading
import time
import logging

logger = logging.getLogger(__name__)


class LLMKeyManager:
    """
    Manage one or more LLM API keys with simple round-robin rotation
    and short-term blacklisting when a key fails (quota/403/etc.).

    Usage:
      mgr = LLMKeyManager("key1,key2")
      key = mgr.get_key()
      mgr.mark_key_failed(key, cooldown_seconds=60)
    """

    def __init__(self, keys_string: Optional[str] = None, keys: Optional[List[str]] = None):
        # keys can be provided as a comma separated string or a list
        if keys is None:
            keys = []
        if keys_string:
            parsed = [k.strip() for k in keys_string.split(",") if k and k.strip()]
            keys = parsed + keys

        self._keys: List[str] = [k for k in keys if k]
        self._lock = threading.Lock()
        self._index = 0
        # blacklist maps key -> expiry_timestamp
        self._blacklist: dict[str, float] = {}

    def _cleanup_blacklist(self) -> None:
        now = time.time()
        expired = [k for k, exp in self._blacklist.items() if exp <= now]
        for k in expired:
            del self._blacklist[k]

    def total_keys(self) -> int:
        return len(self._keys)

    def get_key(self) -> Optional[str]:
        """Return the next available (non-blacklisted) key using round-robin.

        Returns None if no keys are configured or all are blacklisted.
        """
        with self._lock:
            if not self._keys:
                return None

            self._cleanup_blacklist()

            n = len(self._keys)
            for _ in range(n):
                key = self._keys[self._index % n]
                self._index = (self._index + 1) % n
                if key not in self._blacklist:
                    return key

            # no available keys
            return None

    def mark_key_failed(self, key: str, cooldown_seconds: int = 60) -> None:
        """Mark a key as failed and blacklist it for cooldown_seconds."""
        if not key:
            return

        with self._lock:
            expiry = time.time() + max(0, int(cooldown_seconds))
            self._blacklist[key] = expiry
            logger.warning(f"LLM key marked failed and blacklisted for {cooldown_seconds}s: {key[:8]}...")

    def add_keys_from_string(self, keys_string: str) -> None:
        with self._lock:
            parsed = [k.strip() for k in keys_string.split(",") if k and k.strip()]
            for k in parsed:
                if k and k not in self._keys:
                    self._keys.append(k)

    def get_all_keys(self) -> List[str]:
        with self._lock:
            return list(self._keys)
