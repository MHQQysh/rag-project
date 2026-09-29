import os
from dataclasses import dataclass, field

import yaml
from dotenv import dotenv_values

from .data import ROOT


@dataclass
class ModelConfig:
    api_key: str = field(repr=False, default="")
    base_url: str = "https://api.openai.com/v1"
    model: str = ""
    source: str = "未配置"

    def public(self):
        return {"configured": bool(self.api_key and self.model), "model": self.model, "source": self.source}


def load_model() -> ModelConfig:
    env = {**dotenv_values(ROOT.parent / ".env"), **dotenv_values(ROOT / ".env"), **os.environ}
    if env.get("OPENAI_API_KEY"):
        return ModelConfig(
            env["OPENAI_API_KEY"],
            env.get("OPENAI_BASE_URL") or "https://api.openai.com/v1",
            env.get("OPENAI_MODEL") or "gpt-4.1-mini",
            "本项目/工作区环境配置",
        )
    existing = ROOT.parent / "deer-flow" / "config.yaml"
    if existing.exists():
        deer_env = {
            **dotenv_values(existing.parent / ".env"),
            **dotenv_values(existing.parent / ".deepseek.env"),
            **env,
        }
        config = yaml.safe_load(existing.read_text(encoding="utf-8")) or {}
        for model in config.get("models", []):
            key = model.get("api_key", "")
            if isinstance(key, str) and key.startswith("$"):
                key = deer_env.get(key.lstrip("$").strip("{}"), "")
            if (
                key
                and isinstance(key, str)
                and not any(x in key.lower() for x in ("your-api", "your_api", "xxx"))
            ):
                return ModelConfig(
                    key,
                    model.get("api_base") or model.get("base_url") or "https://api.deepseek.com",
                    model.get("model") or model["name"],
                    "复用 DeerFlow config.yaml（只读）",
                )
    return ModelConfig()
