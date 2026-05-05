"""Deep-research orchestration via Anthropic SDK + Web Search tool.

Reads ./out/mindmap.md as outline, runs an integrated deep-research pass,
and writes ./out/report.md.

NOTE: This calls the Anthropic API directly (token-billed). For Max-plan
in-budget execution, prefer running a Claude Code interactive session and
delegating to a `general-purpose` agent.

Usage:
    python scripts/deep_research_claude.py
    python scripts/deep_research_claude.py --input <md> --output <md>
"""
from __future__ import annotations

import argparse
import os
import pathlib

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

SYSTEM = """\
あなたはディープリサーチ・エージェントです。

与えられたアウトラインの各ノードについて：
1. web_search で 3-5 件の信頼できる情報源を検索
2. 各情報源の内容を要約（事実のみ、出典 URL を明記）
3. ノードごとに小見出し付きで統合
4. 最後に全体のエグゼクティブサマリーを付ける

出力は Markdown。出典 URL を本文中に必ず含めること。
"""

DEFAULT_INPUT = "./out/mindmap.md"
DEFAULT_OUTPUT = "./out/report.md"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ERROR: ANTHROPIC_API_KEY is not set")

    outline = pathlib.Path(args.input).read_text(encoding="utf-8")

    client = anthropic.Anthropic()

    # NOTE: Implement the full tool_use loop for production. The simplified
    # call below works for many cases because Anthropic's web_search is a
    # server-side tool (not requiring client-side tool_result roundtrips
    # in the legacy way), but verify against current Anthropic SDK docs.
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[
            {
                "role": "user",
                "content": (
                    "以下のアウトラインで深掘り調査を行い、出典付きの統合レポートを"
                    "Markdown で書いてください。\n\n"
                    "---\n\n"
                    f"{outline}"
                ),
            }
        ],
    )

    # Extract the final text block
    text_blocks = [b.text for b in response.content if hasattr(b, "text")]
    report = "\n\n".join(text_blocks)

    pathlib.Path(args.output).write_text(report, encoding="utf-8")
    print(f"Wrote {args.output} ({len(report)} chars)")


if __name__ == "__main__":
    main()
