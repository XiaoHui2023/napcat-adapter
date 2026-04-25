from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from napcat import GroupMessageEvent, NapCatClient, PrivateMessageEvent, Text


def require_env(name: str) -> str:
    """读取必填环境变量。

    Args:
        name: 环境变量名

    Returns:
        str: 环境变量值

    Raises:
        SystemExit: 变量不存在或为空时退出
    """
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"缺少必填环境变量：{name}")
    return value


async def main() -> None:
    """运行 NapCat SDK 连通性测试。

    Returns:
        None: 持续打印收到的测试消息
    """
    load_dotenv()
    client = NapCatClient(
        ws_url=require_env("NAPCAT_WS_URL"),
        token=os.getenv("NAPCAT_TOKEN"),
    )

    async for event in client:
        match event:
            case PrivateMessageEvent(sender=sender, message=[Text(text="/ping")]):
                print(f"[私聊] {sender.nickname}: /ping")
                await event.send_msg("pong")
            case GroupMessageEvent(
                group_id=gid,
                sender=sender,
                message=[Text(text="/ping")],
            ):
                print(f"[群:{gid}] {sender.nickname}: /ping")
                await event.reply("pong", at=True)
            case GroupMessageEvent(group_id=gid, sender=sender, raw_message=raw_message):
                print(f"[群:{gid}] {sender.nickname}: {raw_message}")
            case PrivateMessageEvent(sender=sender, raw_message=raw_message):
                print(f"[私聊] {sender.nickname}: {raw_message}")
            case _:
                continue


if __name__ == "__main__":
    asyncio.run(main())
