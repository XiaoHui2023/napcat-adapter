from typing import List, Union, Optional
from core.models import (
    BaseSegment,
    TextSegment,
    ImageSegment,
    FaceSegment,
    AtSegment,
    ForwardSegment,
    ReplySegment,
    JsonSegment,
    VideoSegment,
    MfaceSegment,
    LocationSegment,
    BotMessage,
    MessageType,
)
import onebot_protocol
from onebot_protocol import MessagePayload
import logging

logger = logging.getLogger(__name__)

SEGMENT_MAP = {
    "text": TextSegment,
    "image": ImageSegment,
    "face": FaceSegment,
    "at": AtSegment,
    "forward": ForwardSegment,
    "reply": ReplySegment,
    "json": JsonSegment,
    "video": VideoSegment,
    "mface": MfaceSegment,
    "location": LocationSegment,
}

USER_MAP: dict[str,str] = {} # 用户QQ -> 用户昵称

MENTION_ALL_NAME = "全体成员"

def data_to_segments(data_list:list[dict], bot_name:str, bot_id:str) -> list[BaseSegment]:
    """将数据转换为BotMessage对象"""
    segments = [_cast_segment(x) for x in data_list]
    segments = [x for x in segments if x]

    # 提取@机器人的片段
    segments = [(_extract_mention_robot(x,bot_name,bot_id) if isinstance(x,TextSegment) else [x]) for x in segments]
    segments = [x for data in segments for x in data]

    return segments

def onebot_to_bot(payload: MessagePayload) -> BotMessage:
    """将 MessagePayload 转换为 BotMessage"""
    data_list = []
    for message in payload.messages:
        if isinstance(message, onebot_protocol.TextMessageSegment):
            message = TextSegment(data={"text":message.data.text})
        elif isinstance(message, onebot_protocol.MentionMessageSegment):
            name = USER_MAP.get(message.data.user_id)
            if not name:
                logging.warning(f"用户昵称不存在: {message.data.user_id}")
                continue
            message = AtSegment(data={"qq":message.data.user_id, "name":name})
        data_list.append(message.model_dump())

    msg = BotMessage(
        message_id=payload.message_id,
        data_list=data_list,
        message_type=payload.source_type,
        bot_id=payload.bot_id,
        session_id=payload.session_id,
        user_name=payload.user_id or "",
    )

    # 群消息增加艾特
    if msg.message_type == MessageType.GROUP:
        # 指定用户名时，艾特对应用户
        if msg.user_name:
            msg.data_list = [
                AtSegment(data={"qq":msg.user_name, "name":USER_MAP.get(msg.user_name, "")}).model_dump(),
                TextSegment(data={"text":" "}).model_dump(), # 添加空格，避免艾特机器人后，消息段连续
            ] + msg.data_list
    
    return msg

def bot_to_onebot(msg: BotMessage) -> Optional[MessagePayload]:
    """将 BotMessage 转换为 MessagePayload"""
    global USER_MAP

    # 转换为消息段
    segments = data_to_segments(msg.data_list, msg.bot_name, msg.bot_id)

    # 如果是群消息，必须艾特机器人
    if not _should_broadcast(msg, segments):
        return None

    # 去掉艾特机器人
    for segment in segments:
        if isinstance(segment, AtSegment) and segment.qq == msg.bot_id:
            segments.remove(segment)

    messages = []
    for segment in segments:
        if isinstance(segment, TextSegment):
            text = segment.text.strip()
            if not text:
                continue
            message = onebot_protocol.TextMessageSegment(data={"text":text})
        elif isinstance(segment, AtSegment):
            if segment.name == MENTION_ALL_NAME:
                message = onebot_protocol.MentionAllMessageSegment()
            else:
                message = onebot_protocol.MentionMessageSegment(data={"user_id":segment.qq})
            # 记录用户昵称
            USER_MAP[segment.qq] = segment.name
        else:
            continue
        messages.append(message)

    if not messages:
        return None

    return MessagePayload(
        message_id=msg.message_id,
        source_type=msg.message_type,
        bot_id=msg.bot_id,
        session_id=msg.session_id,
        user_id=msg.user_name,
        messages=messages,
    )

def _should_broadcast(msg: BotMessage, segments:list[BaseSegment]) -> bool:
    """是否应该广播"""
    if msg.message_type == MessageType.GROUP:
        for segment in segments:
            if isinstance(segment, AtSegment) and segment.qq == msg.bot_id:
                return True
        return False
    return True

def _cast_segment(data:dict) -> Optional[BaseSegment]:
    """转换消息数据为Segment对象"""
    cls = SEGMENT_MAP.get(data["type"])
    if not cls:
        logging.warning(f"未知的消息类型: {data}")
        return None
    try:
        return cls(**data)
    except:
        logging.exception(f"转换消息数据失败: {data}")
        return None

def _extract_mention_robot(text:TextSegment,bot_name:str,bot_id:str) -> List[Union[TextSegment, AtSegment]]:
    '''
    提取消息中@机器人的片段
    text: 消息
    bot_name: 机器人昵称
    bot_id: 机器人ID

    如果有，则拆成 [前消息,@机器人,后消息]
    如果没有，则返回 [消息]
    '''
    def split(text:TextSegment) -> List[Union[TextSegment, AtSegment]]:
        # unpack
        content = text.text

        # 提取@机器人的片段
        keyword = f"@{bot_name} "
        if keyword in content:
            # 提取@机器人的片段
            index = content.find(keyword)
            # 提取前消息
            before_text = content[:index]
            # 提取后消息
            after_text = content[index + len(keyword):]
            # 返回
            return split(TextSegment(data={"text":before_text})) + [AtSegment(data={"name":bot_name, "qq":bot_id})] + split(TextSegment(data={"text":after_text}))
        else:
            return [text]

    try:
        return split(text)
    except:
        logging.exception(f"提取@机器人的片段失败: {text}")
        return [text]
