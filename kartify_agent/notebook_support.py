"""Compact display helpers so notebook cells focus on experiments and interpretation."""

from __future__ import annotations

from typing import Any

import pandas as pd
from IPython.display import Markdown, display

from .agent import ARCHITECTURE_MERMAID, SupportSession


def show_architecture() -> None:
    display(Markdown(f"```mermaid\n{ARCHITECTURE_MERMAID}\n```"))


def show_turn(result: dict[str, Any]) -> None:
    display(Markdown(f"### Agent response\n{result['response']}"))
    display(pd.DataFrame(result.get("trace", [])))
    display(pd.Series(result.get("quality", {}), name="value").to_frame())


def run_conversation(session: SupportSession, prompts: list[str]) -> pd.DataFrame:
    for prompt in prompts:
        result = session.ask(prompt)
        print(f"\nUSER: {prompt}\nAGENT: {result['response']}")
    return pd.DataFrame(session.history)
