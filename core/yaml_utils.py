from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "config.yaml"

def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config() -> dict:
    data = load_yaml(CONFIG_PATH)
    if not isinstance(data, dict):
        return {}
    return data


def get_sources_platform_ids() -> list[str]:
    """
    从 config.yaml 的 sources 字段读取平台 ID 列表
    """
    config = load_config()
    sources = config.get("sources", []) or []
    return [item.get("id") for item in sources if isinstance(item, dict) and item.get("id")]

