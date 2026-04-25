import argparse
import asyncio

from log import setup_logging, setup_log_filter
from core import Bot, BotMessage, onebot_to_bot, bot_to_onebot
from settings import load_settings, settings
from onebot_protocol import MessagePayload
from patch_jack import Jack, LoggingJackListener


def parse_args() -> argparse.Namespace:
    """解析命令行参数。

    Returns:
        argparse.Namespace: 启动参数
    """
    p = argparse.ArgumentParser(description="NapCat 对接")
    p.add_argument("config", nargs="?", help="配置文件路径")
    return p.parse_args()


async def main() -> None:
    """启动 NapCat 适配器与网关服务。

    Returns:
        None: 服务退出时完成资源清理
    """
    args = parse_args()
    if args.config:
        load_settings(args.config)

    setup_logging(log_dir=settings.log_dir, level=settings.log_level)
    setup_log_filter()

    bot = Bot(ws_url=settings.napcat_ws_url, token=settings.napcat_token)
    jack = Jack(port=settings.server_port, listeners=[LoggingJackListener()])

    @jack
    async def _(payload: MessagePayload) -> None:
        """把网关消息投递到 NapCat。"""
        msg = onebot_to_bot(payload)
        await bot.send(msg)

    @bot.on_message
    async def _(msg: BotMessage) -> None:
        """把 NapCat 消息投递到网关。"""
        payload = bot_to_onebot(msg)
        if not payload:
            return
        await jack.send(payload)

    await bot.start()
    try:
        await jack.run()
    finally:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
