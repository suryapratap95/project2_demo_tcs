"""Prompt version control via YAML files.

Loads prompt templates from the prompts/ directory, tracks versions,
and supports diffing and rollback. Every prompt is a YAML file with
metadata (version, author, tags) and the template text.
"""
import os
from functools import lru_cache
from pathlib import Path

import yaml

from .logging_utils import get_logger, log_event

logger = get_logger("prompt_registry")

PROMPTS_DIR = Path(os.getenv("PROMPTS_DIR", "./prompts"))


class PromptTemplate:
    def __init__(self, name: str, data: dict, file_path: Path):
        self.name = name
        self.version = data.get("version", "0.0")
        self.description = data.get("description", "")
        self.author = data.get("author", "unknown")
        self.updated = data.get("updated", "unknown")
        self.tags = data.get("tags", [])
        self.template = data.get("template", "")
        self.system_template = data.get("system_template", "")
        self.human_template = data.get("human_template", "")
        self.variables = data.get("variables", [])
        self.examples = data.get("examples", [])
        self.file_path = file_path
        self._raw = data

    def render(self, **kwargs) -> str:
        text = self.template or self.system_template
        for key, value in kwargs.items():
            text = text.replace(f"{{{key}}}", str(value))
        return text

    def get_metadata(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "updated": self.updated,
            "tags": self.tags,
            "variables": self.variables,
            "file_path": str(self.file_path),
        }


class PromptRegistry:
    def __init__(self, prompts_dir: Path = PROMPTS_DIR):
        self._dir = prompts_dir
        self._prompts: dict[str, PromptTemplate] = {}
        self._load_all()

    def _load_all(self) -> None:
        if not self._dir.exists():
            log_event(logger, "prompts directory not found", path=str(self._dir))
            return
        for yaml_file in sorted(self._dir.glob("*.yaml")):
            self._load_file(yaml_file)
        log_event(logger, "prompt registry loaded", count=len(self._prompts))

    def _load_file(self, file_path: Path) -> None:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return
        name = data.get("name", file_path.stem)
        self._prompts[name] = PromptTemplate(name=name, data=data, file_path=file_path)

    def get(self, name: str) -> PromptTemplate:
        if name not in self._prompts:
            raise KeyError(f"Prompt '{name}' not found in registry. Available: {list(self._prompts.keys())}")
        return self._prompts[name]

    def list_all(self) -> list[dict]:
        return [p.get_metadata() for p in self._prompts.values()]

    def reload(self) -> None:
        self._prompts.clear()
        self._load_all()

    def diff(self, name: str, new_template: str) -> dict:
        current = self.get(name)
        current_lines = (current.template or current.system_template).strip().splitlines()
        new_lines = new_template.strip().splitlines()
        added = [l for l in new_lines if l not in current_lines]
        removed = [l for l in current_lines if l not in new_lines]
        return {"added": added, "removed": removed, "current_version": current.version}


@lru_cache(maxsize=1)
def get_registry() -> PromptRegistry:
    return PromptRegistry()
