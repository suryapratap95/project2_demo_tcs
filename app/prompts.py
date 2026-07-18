"""Prompt management - loads from versioned YAML files via the prompt registry.

This module provides backward-compatible access to prompts. The actual
prompt content lives in prompts/*.yaml files for version control,
diffing, and rollback. This module is the runtime interface.
"""
from .prompt_registry import get_registry

registry = get_registry()

_system = registry.get("finbot_system_prompt")
_examples = registry.get("few_shot_examples")

FEW_SHOT_EXAMPLES = _examples.examples

SYSTEM_PROMT = _system.template
for _example in FEW_SHOT_EXAMPLES:
    SYSTEM_PROMT += f"\n    Customer: {_example['input']}\n    FinBot: {_example['output']}\n"
