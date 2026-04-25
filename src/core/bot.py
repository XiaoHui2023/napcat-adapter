import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

from napcat import GroupMessageEvent, NapCatClient, PrivateMessageEvent
from napcat.types.messages import Message, MessageSegment, UnknownMessageSegment
from pydantic import BaseModel, Field, PrivateAttr

from core.models import BotMessage, MessageType

logger = logging.getLogger(__name__)


class Bot(BaseModel):
    """连接 NapCat 并保持旧网关侧 Bot 接口。"""

    ws_url: str = Field(description="NapCat 正向 WebSocket 地址")
    token: str | None = Field(default=None, description="NapCat 访问令牌")
    max_event_cache: int = Field(default=100, description="最大事件缓存数量")

    _stop_event: asyncio.Event = PrivateAttr()
    _task: asyncio.Task[None] | None = PrivateAttr(default=None)
    _client: NapCatClient | None = PrivateAttr(default=None)
    _login_info: dict[str, Any] | None = PrivateAttr(default=None)
    _bot_name: str = PrivateAttr(default="")
    _bot_id: str = PrivateAttr(default="")
    _running: bool = PrivateAttr(default=False)
    _on_message: Callable[[BotMessage], Awaitable[None]] | None = PrivateAttr(default=None)

    def model_post_init(self, ctx: Any) -> None:
        """初始化运行期对象。

        Args:
            ctx: Pydantic 初始化上下文

        Returns:
            None: 完成运行期状态初始化
        """
        self._stop_event = asyncio.Event()

    def on_message(self, callback: Callable[[BotMessage], Awaitable[None]]) -> None:
        """设置收到消息后的回调函数。

        Args:
            callback: 接收统一消息模型的异步回调

        Returns:
            None: 回调会被保存并在收到消息时调用
        """
        self._on_message = callback

    async def _refresh_login_info(self) -> None:
        """按 NapCat 登录信息接口刷新机器人基础信息。"""
        if self._client is None:
            return
        try:
            login_info = await self._client.get_login_info()
            user_id = int(login_info["user_id"])
            self._client.self_id = user_id
            self._login_info = dict(login_info)
            self._bot_id = str(user_id)
            self._bot_name = str(login_info["nickname"])
            logging.info("机器人登录: %s (%s)", self._bot_name, self._bot_id)
        except Exception:
            logging.exception("获取登录信息失败")

    async def _handle_events(self) -> None:
        """连接 NapCat 并持续消费消息事件。"""
        self._client = NapCatClient(ws_url=self.ws_url, token=self.token)
        logger.info("正在连接 NapCat: %s", self.ws_url)

        try:
            async with self._client:
                await self._refresh_login_info()
                async for event in self._client:
                    if self._stop_event.is_set():
                        break
                    if isinstance(event, (GroupMessageEvent, PrivateMessageEvent)):
                        await self._handle_message(event)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("NapCat 事件循环异常")
        finally:
            self._running = False
            self._client = None

    async def _handle_message(self, event: GroupMessageEvent | PrivateMessageEvent) -> None:
        """把 NapCat 消息事件转换成网关侧统一消息。"""
        if self._login_info is None:
            await self._refresh_login_info()

        user_name = str(event.user_id)
        session_id = str(event.group_id) if isinstance(event, GroupMessageEvent) else user_name
        message_type = MessageType.GROUP if isinstance(event, GroupMessageEvent) else MessageType.PRIVATE
        data_list = [dict(segment) for segment in event.message]

        logger.info("收到消息: [%s-%s] %s", session_id, user_name, data_list)

        message = BotMessage(
            session_id=session_id,
            data_list=data_list,
            bot_id=self._bot_id,
            message_type=message_type,
            user_name=user_name,
            message_id=str(event.message_id),
            bot_name=self._bot_name,
        )

        if self._on_message is None:
            return
        try:
            await self._on_message(message)
        except Exception:
            logging.exception("消息回调失败")

    async def start(self) -> None:
        """启动 NapCat 事件消费任务。

        Returns:
            None: 后台任务会持续运行直到停止
        """
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._task = asyncio.create_task(self._handle_events())

    async def send(self, message: BotMessage) -> None:
        """按统一消息模型发送 NapCat 消息。

        Args:
            message: 网关侧传入的统一消息

        Returns:
            None: 消息会投递到对应私聊或群会话
        """
        if self._client is None or not self._client.is_running:
            logger.warning("NapCat 尚未连接，消息未发送")
            return

        data_list = [
            {"type": segment["type"], "data": segment.get("data", {})}
            for segment in message.data_list
        ]
        messages = _to_napcat_messages(data_list)
        if not messages:
            logger.warning("没有可发送的消息段: %s", data_list)
            return

        logger.info("发送消息: [%s] %s", message.session_id, data_list)
        try:
            if message.message_type == MessageType.GROUP:
                await self._client.send_group_msg(
                    group_id=message.session_id, message=messages
                )
            else:
                await self._client.send_private_msg(
                    user_id=message.session_id, message=messages
                )
        except Exception:
            logger.exception("发送消息失败")

    async def stop(self) -> None:
        """停止事件消费并关闭连接。

        Returns:
            None: 后台任务会被取消并等待清理完成
        """
        if not self._running:
            return
        logger.info("正在停止 Bot...")
        self._stop_event.set()
        if self._task is not None and self._task is not asyncio.current_task():
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        self._running = False

    async def run(self) -> None:
        """启动服务并阻塞到停止信号。

        Returns:
            None: 停止后会释放连接资源
        """
        await self.start()
        try:
            await self._stop_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()


def _to_napcat_messages(data_list: list[dict[str, Any]]) -> list[Message]:
    """把 OneBot 字典消息段转换成 NapCat SDK 消息段。

    Args:
        data_list: 网关侧统一消息段列表

    Returns:
        list[Message]: 可被 NapCat SDK 发送的消息段
    """
    messages: list[Message] = []
    for data in data_list:
        segment = MessageSegment.from_dict(data)
        if isinstance(segment, UnknownMessageSegment):
            logger.warning("跳过不支持的消息段: %s", data.get("type"))
            continue
        messages.append(segment)
    return messages