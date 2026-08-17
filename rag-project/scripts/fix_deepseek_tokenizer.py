"""Correct the tokenizer class metadata in the ModelScope mirror.

The mirrored DeepSeek R1 Distill Qwen repository declares LlamaTokenizerFast
even though tokenizer.json is a Qwen2 BPE tokenizer. New Transformers releases
then select the slow Llama tokenizer, which cannot encode Chinese text and
causes vLLM to stream raw Ġ/Ċ byte-level tokens.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    model_dir = Path(sys.argv[1])
    path = model_dir / "tokenizer_config.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    previous = config.get("tokenizer_class")
    config["tokenizer_class"] = "Qwen2TokenizerFast"
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"tokenizer_class: {previous} -> Qwen2TokenizerFast")


if __name__ == "__main__":
    main()
