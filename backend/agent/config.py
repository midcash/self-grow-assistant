"""配置加载器 — YAML 驱动 + 环境变量替换

参考 2026 主流: 配置驱动设计，支持 ${ENV_VAR} 替换
"""

import os
import re
from pathlib import Path
from typing import Any


class ConfigLoader:
    """YAML 配置加载器

    支持:
    - YAML 文件加载
    - ${ENV_VAR} 环境变量替换
    - 默认值合并
    """

    @staticmethod
    def load(config_path: str | Path) -> dict[str, Any]:
        """加载 YAML 配置文件"""
        import yaml
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        return ConfigLoader._resolve_env_vars(raw)

    @staticmethod
    def _resolve_env_vars(data: Any) -> Any:
        """递归解析 ${ENV_VAR} 环境变量"""
        if isinstance(data, dict):
            return {k: ConfigLoader._resolve_env_vars(v) for k, v in data.items()}
        if isinstance(data, list):
            return [ConfigLoader._resolve_env_vars(item) for item in data]
        if isinstance(data, str):
            pattern = re.compile(r'\$\{(\w+)\}')
            def replacer(match):
                var_name = match.group(1)
                return os.environ.get(var_name, match.group(0))
            return pattern.sub(replacer, data)
        return data

    @staticmethod
    def get_default_config() -> dict[str, Any]:
        """返回默认配置 (当没有 YAML 文件时)"""
        return {
            "agent": {
                "name": "self-grow-agent",
                "cron": "*/20 * * * *",
            },
            "plugins": {
                "llm": {
                    "default": "deepseek",
                    "deepseek": {
                        "api_base": "https://api.deepseek.com/v1",
                        "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
                        "model": "deepseek-chat",
                        "max_tokens": 4096,
                    },
                },
                "tts": {
                    "default": "qwen",
                    "fallback": "edge",
                },
                "priority": {
                    "urgency_lambda": 0.15,
                    "long_task_factor": 2.0,
                    "algorithm_weight": 0.6,
                    "llm_weight": 0.4,
                },
            },
            "memory": {
                "hot_max_tokens": 4096,
            },
        }
