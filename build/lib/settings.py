from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Literal
from pathlib import Path
import yaml

def find_env_file() -> Path | None:
    """从当前文件所在目录开始，逐层向上查找 .env"""
    start = Path(__file__).resolve().parent
    for parent in [start, *start.parents]:
        env_file = parent / ".env"
        if env_file.is_file():
            return env_file
    return None

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        env_file_encoding="utf-8",
    )
    
    """机器人主机"""
    bot_port: int = 6199
    """机器人端口"""
    server_port: int = 8080
    """服务器端口"""
    log_level: Literal['info', 'debug', 'warning', 'error', 'critical']='info'
    """日志级别"""
    log_dir: str|None = Field(default=None)
    """日志目录，不指定则仅控制台"""

settings = Settings()

def load_settings(input_yaml:str|None):
    """加载配置文件"""
    global settings

    if input_yaml:
        with open(input_yaml, encoding='utf-8') as f:
            local_overrides = yaml.safe_load(f)
        for key, value in local_overrides.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

__all__ = [
    "settings",
    "load_settings",
]