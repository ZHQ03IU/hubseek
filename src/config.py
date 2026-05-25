import os
import json
from pathlib import Path
from typing import Optional

# Default config path: ~/.github-finder/config.json
DEFAULT_CONFIG_DIR = Path.home() / ".github-finder"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"

# Default configuration values
DEFAULT_CONFIG = {
    "openai_api_key": "",
    "openai_base_url": "https://api.openai.com/v1",
    "model": "gpt-4o-mini",
    "github_token": "",
    "max_results": 20,
    "final_recommendations": 5,
    "cache_ttl_hours": 24,
    "readme_max_chars": 2500
}


def get_config_path(custom_path: Optional[str] = None) -> Path:
    """Get config file path, with optional custom path override."""
    if custom_path:
        return Path(custom_path)
    return DEFAULT_CONFIG_FILE


def ensure_config_dir(config_path: Path) -> None:
    """Create config directory if it doesn't exist."""
    config_path.parent.mkdir(parents=True, exist_ok=True)


def load_config(config_path: Optional[str] = None) -> dict:
    """
    Load configuration with environment variable fallback.
    Priority: Environment Variables > Config File > Defaults
    """
    path = get_config_path(config_path)
    config = DEFAULT_CONFIG.copy()

    # Load from config file if exists
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                file_config = json.load(f)
                config.update(file_config)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load config file {path}: {e}")

    # Environment variables override config file
    env_mapping = {
        "OPENAI_API_KEY": "openai_api_key",
        "OPENAI_BASE_URL": "openai_base_url",
        "OPENAI_MODEL": "model",
        "GITHUB_TOKEN": "github_token",
        "GITHUB_FINDER_MAX_RESULTS": "max_results",
        "GITHUB_FINDER_RECOMMENDATIONS": "final_recommendations",
        "GITHUB_FINDER_CACHE_TTL": "cache_ttl_hours",
        "GITHUB_FINDER_README_MAX_CHARS": "readme_max_chars"
    }

    for env_var, config_key in env_mapping.items():
        env_value = os.environ.get(env_var)
        if env_value is not None:
            # Convert numeric values
            if config_key in ("max_results", "final_recommendations", "cache_ttl_hours", "readme_max_chars"):
                try:
                    config[config_key] = int(env_value)
                except ValueError:
                    pass
            else:
                config[config_key] = env_value

    return config


def save_config(config: dict, config_path: Optional[str] = None) -> None:
    """Save configuration to file."""
    path = get_config_path(config_path)
    ensure_config_dir(path)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def create_default_config(config_path: Optional[str] = None) -> Path:
    """Create default config file if it doesn't exist."""
    path = get_config_path(config_path)
    if not path.exists():
        save_config(DEFAULT_CONFIG, config_path)
    return path


def validate_config(config: dict) -> list[str]:
    """Validate config and return list of errors."""
    errors = []

    if not config.get("openai_api_key"):
        errors.append("OpenAI API key is required (set OPENAI_API_KEY or configure in config file)")

    if not config.get("github_token"):
        errors.append("GitHub token is required (set GITHUB_TOKEN or configure in config file)")

    if config.get("max_results", 0) < 1:
        errors.append("max_results must be at least 1")

    if config.get("final_recommendations", 0) < 1:
        errors.append("final_recommendations must be at least 1")

    return errors
