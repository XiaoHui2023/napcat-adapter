from aiocqhttp import CQHttp, Event
from aiocqhttp.exceptions import ActionFailed
import logging
from typing import Callable, Awaitable
from models import BotMessage, MessageType
from pydantic import BaseModel
import aiohttp
import asyncio
import logging

logger = logging.getLogger(__name__)

class Bot(BaseModel):
    port: int
    """机器人端口"""
    max_event_cache: int = 100
    """最大事件缓存数量"""

    def model_post_init(self, ctx) -> None:
        self._stop_event = asyncio.Event()

        self._bot = None
        self._login_info = None
        self._bot_name: str = None
        """机器人昵称"""
        self._bot_id: str = None
        """机器人ID"""
        self._running = False
        self._on_message: Callable[[BotMessage], Awaitable[None]] = None

    def on_message(self, callback: Callable[[BotMessage], Awaitable[None]]) -> None:
        """设置消息回调函数"""
        self._on_message = callback

    async def _get_login_info(self):
        try:
            self._login_info = await self._bot.get_login_info()
            self._bot_name = self._login_info["nickname"]
            self._bot_id = str(self._login_info["user_id"])
        except:
            logging.exception(f"获取登录信息失败")
        logging.info(f"机器人登陆: {self._bot_name} ({self._bot_id})")

    async def _handle_ws(self):
        logging.info(f"机器人已启动，监听: {self.port}")

        self._bot = CQHttp(api_root='')

        @self._bot.on_websocket_connection
        async def _(_):
            """连接时获取一次登录信息并缓存"""
            await self._get_login_info()

        # 注册消息处理器
        @self._bot.on_message
        async def _(event: Event,**kwargs):
            # 使用缓存的登录信息，如果没有则尝试获取
            if self._login_info is None:
                await self._get_login_info()

            # 用户id
            user_name = str(event.user_id)
            # 会话id
            session_id = str(event.group_id) if event.message_type == 'group' else user_name
            # 会话类型
            message_type = MessageType.GROUP if event.message_type == 'group' else MessageType.PRIVATE
            # 消息内容
            data_list = event.message
            # 消息id
            message_id = str(event.message_id)

            logger.info(f"收到消息: [{session_id}-{user_name}] {data_list}")

            # 转换消息数据为Session事务对象
            message = BotMessage(
                session_id=session_id,
                data_list=data_list,
                bot_id=self._bot_id,
                message_type=message_type,
                user_name=user_name,
                message_id=message_id,
                bot_name=self._bot_name,
            )

            # 回调
            try:
                await self._on_message(message)
            except:
                logging.exception(f"消息回调失败")

        # 注册错误处理器
        @self._bot.on('error')
        async def _(event: Event):
            logging.error(f'bot发生错误: {event.message}')
        
        await self._bot.run_task(
            host='0.0.0.0',
            port=self.port,
            shutdown_trigger=self._stop_event.wait,
        )

    async def start(self):
        if self._running:
            return
        self._running = True
        self._session = aiohttp.ClientSession()
        asyncio.create_task(self._handle_ws())

    async def send(self,message:BotMessage) -> None:
        """发送消息（使用 send_msg，无需原始 Event；会话信息来自 BotMessage）"""
        # 仅保留type和data
        data_list = [{"type":segment["type"], "data":segment.get("data", {})} for segment in message.data_list]

        logger.info(f"发送消息: [{message.session_id}] {data_list}")
        try:
            sid = int(message.session_id)
            if message.message_type == MessageType.GROUP:
                await self._bot.send_msg(
                    message_type="group",
                    group_id=sid,
                    message=data_list,
                )
            else:
                await self._bot.send_msg(
                    message_type="private",
                    user_id=sid,
                    message=data_list,
                )
        except:
            logger.exception(f"发送消息失败")

    async def stop(self):
        """优雅停止 Bot：取消心跳和所有后台任务，关闭 WebSocket"""
        if not self._running:
            return
        logger.info("正在停止 Bot...")
        self._running = False
        self._stop_event.set()
            
    async def run(self):
        """启动服务并阻塞，直到中断"""
        await self.start()
        try:
            await self._stop_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()