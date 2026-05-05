"""Convert a mind-map image to hierarchical Markdown using Claude Vision.

Usage:
    python scripts/img_to_md_claude.py <image_path> <output_md_path>
"""
from __future__ import annotations

import base64
import os
import pathlib
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

PROMPT = """\
添付はマインドマップの画像です。階層構造を Markdown に転写してください。

ルール:
- ルートノードを `# 見出し` とする
- 第2階層を `## 見出し`、第3階層以降は `- 箇条書き` の入れ子で表現
- すべての枝・葉ノードを漏らさず転写
- 図中の左→右、上→下の順序を保持
- 画像から読み取れない部分は推測せず `[unreadable]` と記す

出力は Markdown 本体のみ。前後に説明文・コードフェンスを付けない。
"""


def main(image_path: str, output_path: str) -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ERROR: ANTHROPIC_API_KEY is not set")

    image_bytes = pathlib.Path(image_path).read_bytes()
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
    )

    text = msg.content[0].text
    pathlib.Path(output_path).write_text(text, encoding="utf-8")
    print(f"Wrote {output_path} ({len(text)} chars)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: img_to_md_claude.py <image_path> <output_md_path>")
    main(sys.argv[1], sys.argv[2])
