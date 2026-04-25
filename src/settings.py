from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file() -> Path | None:
    """从当前文件所在目录开始向上查找环境配置。

    Returns:
        Path | None: 找到时返回配置路径，否则返回 None
    """
    start = Path(__file__).resolve().parent
    for parent in [start, *start.parents]:
        env_file = parent / ".env"
        if env_file.is_file():
            return env_file
    return None


class Settings(BaseSettings):
    """保存 NapCat 适配器的用户配置。"""

    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    napcat_ws_url: str = Field(description="NapCat 正向 WebSocket 地址")
    napcat_token: str | None = Field(default=None, description="NapCat 访问令牌")
    server_port: int = Field(default=8080, description="网关服务端口")
    log_level: Literal["info", "debug", "warning", "error", "critical"] = Field(
        default="info", description="日志级别"
    )
    log_dir: str | None = Field(default=None, description="日志目录，不填写时仅输出到控制台")

settings = Settings()


def load_settings(input_yaml: str | None) -> None:
    """加载本地配置文件并覆盖当前设置。

    Args:
        input_yaml: YAML 配置文件路径

    Returns:
        None: 已知配置项会写回全局设置对象
    """
    global settings

    if input_yaml:
        with open(input_yaml, encoding="utf-8") as f:
            local_overrides: dict[str, Any] = yaml.safe_load(f) or {}
        for key, value in local_overrides.items():
            if hasattr(settings, key):
                setattr(settings, key, value)


__all__ = [
    "settings",
    "load_settings",
]