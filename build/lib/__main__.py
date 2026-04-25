import argparse
import asyncio
from log import setup_logging, setup_log_filter
from core import Bot, onebot_to_bot, bot_to_onebot
from settings import load_settings, settings
from onebot_protocol import MessagePayload
from patch_jack import Jack, LoggingJackListener
from models import BotMessage

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Lagrange 对接")
    p.add_argument("config", nargs="?", help="配置文件路径")
    return p.parse_args()

async def main():
    args = parse_args()
    if args.config:
        load_settings(args.config)

    setup_logging(log_dir=settings.log_dir, level=settings.log_level)
    setup_log_filter()

    bot = Bot(port=settings.bot_port)
    jack = Jack(port=settings.server_port,listeners=[LoggingJackListener()])

    @jack
    async def _(payload: MessagePayload):
        msg = onebot_to_bot(payload)
        await bot.send(msg)

    @bot.on_message
    async def _(msg: BotMessage):
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
