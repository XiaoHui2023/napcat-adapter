import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from rich.logging import RichHandler

def setup_logging(
    log_dir: Optional[str] = None,
    level: str | int = logging.INFO,
):
    """
    配置全局日志。

    日志始终输出到控制台，如果指定了 log_dir 则同时写入该目录下
    以启动时间命名的日志文件（格式: YYYYMMDD_HHMMSS.log）。

    Args:
        log_dir: 日志输出目录，None 表示仅控制台输出
        level:   日志级别，支持字符串
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    fmt = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    rich_handler = RichHandler(rich_tracebacks=True, show_path=False)
    rich_handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    handlers = [rich_handler]

    if log_dir:
        dir_path = Path(log_dir)
        dir_path.mkdir(parents=True, exist_ok=True)
        filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".log"
        file_handler = logging.FileHandler(dir_path / filename, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        handlers.append(file_handler)

    logging.basicConfig(level=level, format=fmt, datefmt=datefmt, handlers=handlers)


def setup_log_filter():
    """创建过滤器类"""
    
    class LogFilter(logging.Filter):
        def __init__(self, filters):
            self.filters = filters
        
        def filter(self, record):
            # 如果消息包含任何过滤词，则过滤掉
            return not any(f in record.getMessage() for f in self.filters)

    # 使用过滤器
    filters = [
        'meta_event.heartbeat',
        'meta_event.lifecycle.connect',
        'message.group.normal',
        'message.group.recall',
        'message.private.friend',
        "hypercorn.error",
    ]
    logging.getLogger().addFilter(LogFilter(filters))