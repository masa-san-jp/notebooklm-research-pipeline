"""Convert a mind-map image to hierarchical Markdown using a local vision model.

Targets LM Studio Local Server (OpenAI-compatible API). Works with Ollama
0.5+ as well by adjusting LM_STUDIO_URL.

Usage:
    python scripts/img_to_md_local.py <image_path> <output_md_path>
"""
from __future__ import annotations

import base64
import os
import pathlib
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

ENDPOINT = os.environ.get("LM_STUDIO_URL", "http://localhost:1234/v1") + "/chat/completions"
API_KEY = os.environ.get("LM_STUDIO_API_KEY", "lm-studio")
MODEL = os.environ.get("LM_STUDIO_VISION_MODEL", "llava-v1.6-mistral-7b")

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
    img_b64 = base64.standard_b64encode(
        pathlib.Path(image_path).read_bytes()
    ).decode("utf-8")

    payload = {
        "model": MODEL,
        "max_tokens": 4000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
    }

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    response = requests.post(ENDPOINT, json=payload, headers=headers, timeout=300)
    response.raise_for_status()

    text = response.json()["choices"][0]["message"]["content"]
    pathlib.Path(output_path).write_text(text, encoding="utf-8")
    print(f"Wrote {output_path} ({len(text)} chars)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: img_to_md_local.py <image_path> <output_md_path>")
    main(sys.argv[1], sys.argv[2])
