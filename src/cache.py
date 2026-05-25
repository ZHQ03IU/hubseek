import hashlib
import json
from pathlib import Path
from typing import Optional
import diskcache


# Default cache directory
DEFAULT_CACHE_DIR = Path.home() / ".github-finder" / "cache"


class CacheManager:
    """Local cache manager using diskcache."""

    def __init__(self, cache_dir: Optional[str] = None, ttl_hours: int = 24):
        """
        Initialize cache manager.

        Args:
            cache_dir: Cache directory path
            ttl_hours: Cache time-to-live in hours
        """
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl_hours * 3600  # Convert to seconds
        self.cache = diskcache.Cache(str(self.cache_dir))

    def _make_key(self, prefix: str, params: dict) -> str:
        """Generate cache key from prefix and parameters."""
        # Sort params for consistent hashing
        sorted_params = json.dumps(params, sort_keys=True)
        hash_str = f"{prefix}:{sorted_params}"
        return hashlib.md5(hash_str.encode()).hexdigest()

    def get_search_results(self, query: str, max_results: int) -> Optional[list]:
        """Get cached search results."""
        key = self._make_key("search", {"query": query, "max_results": max_results})
        return self.cache.get(key)

    def set_search_results(self, query: str, max_results: int, results: list) -> None:
        """Cache search results."""
        key = self._make_key("search", {"query": query, "max_results": max_results})
        self.cache.set(key, results, expire=self.ttl)

    def get_repo_details(self, full_name: str, readme_max_chars: int) -> Optional[dict]:
        """Get cached repo details."""
        key = self._make_key("repo", {"full_name": full_name, "readme_max_chars": readme_max_chars})
        return self.cache.get(key)

    def set_repo_details(self, full_name: str, readme_max_chars: int, details: dict) -> None:
        """Cache repo details."""
        key = self._make_key("repo", {"full_name": full_name, "readme_max_chars": readme_max_chars})
        self.cache.set(key, details, expire=self.ttl)

    def get_analysis(self, query: str, project_names: list[str]) -> Optional[dict]:
        """Get cached analysis result."""
        key = self._make_key("analysis", {"query": query, "projects": sorted(project_names)})
        return self.cache.get(key)

    def set_analysis(self, query: str, project_names: list[str], analysis: dict) -> None:
        """Cache analysis result."""
        key = self._make_key("analysis", {"query": query, "projects": sorted(project_names)})
        self.cache.set(key, analysis, expire=self.ttl)

    def clear(self) -> None:
        """Clear all cache."""
        self.cache.clear()

    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "volume": self.cache.volume(),
            "directory": str(self.cache_dir)
        }
