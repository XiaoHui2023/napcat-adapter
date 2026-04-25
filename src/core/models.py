from enum import StrEnum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class MessageType(StrEnum):
    PRIVATE = "private"
    GROUP = "group"


class BaseSegment(BaseModel):
    type: str
    data: dict


class AtSegment(BaseSegment):
    type: Literal["at"] = "at"
    qq: str = None
    """qq号"""
    name: str = None
    """昵称"""

    def model_post_init(self, ctx):
        """去掉昵称中的@"""
        self.qq = self.data["qq"]
        self.name = self.data["name"].lstrip("@").strip()


class FaceSegment(BaseSegment):
    type: Literal["face"] = "face"
    id: str = None
    """表情id"""
    large: str = None
    """大图url"""
    result_id: str | None = None
    """表情结果id"""
    chain_count: int | None = None
    """连击数量"""

    def model_post_init(self, ctx):
        self.id = str(self.data["id"])
        self.large = self.data.get("large")
        self.result_id = self.data.get("resultId")
        self.chain_count = self.data.get("chainCount")


class TextSegment(BaseSegment):
    type: Literal["text"] = "text"
    text: str = None
    """文本"""

    def model_post_init(self, ctx):
        self.text = self.data["text"]


class ReplySegment(BaseSegment):
    type: Literal["reply"] = "reply"
    id: str = None
    """回复id"""

    def model_post_init(self, ctx):
        self.id = self.data["id"]


class MfaceSegment(BaseSegment):
    type: Literal["mface"] = "mface"
    url: str = None
    """图片url"""
    emoji_package_id: str = None
    """表情包id"""
    emoji_id: str = None
    """表情id"""
    key: str = None
    """表情包名称"""
    summary: str = None
    """表情包描述"""


class LocationSegment(BaseSegment):
    type: Literal["location"] = "location"
    lat: float = None
    """纬度"""
    lon: float = None
    """经度"""
    title: str = None
    """标题"""
    content: str = None
    """内容"""


class JsonSegment(BaseSegment):
    type: Literal["json"] = "json"


class ImageSegment(BaseSegment):
    type: Literal["image"] = "image"
    file: str = None
    """文件路径"""
    filename: str = None
    """文件名"""
    url: str = None
    """图片url"""
    summary: str = None
    """图片摘要"""
    subType: str = None
    """图片类型"""


class ForwardSegment(BaseSegment):
    type: Literal["forward"] = "forward"
    id: str = None
    """转发id"""


class VideoSegment(BaseSegment):
    type: Literal["video"] = "video"
    file: str = None
    """文件路径"""
    url: str = None
    """视频url"""

    def model_post_init(self, ctx):
        self.file = self.data["file"]
        self.url = self.data["url"]


Segment = Annotated[
    Union[
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
    ],
    Field(discriminator="type"),
]


class BotMessage(BaseModel):
    message_id: str = Field(description="消息id")
    data_list: list[dict] = Field(description="消息数据列表")
    message_type: MessageType = Field(description="消息类型")
    bot_id: str = Field(description="机器人ID")
    bot_name: str | None = Field(None, description="机器人昵称")
    session_id: str = Field(description="会话id")
    user_name: str = Field(description="用户名")


__all__ = [
    "BotMessage",
    "BaseSegment",
    "TextSegment",
    "ImageSegment",
    "FaceSegment",
    "AtSegment",
    "ForwardSegment",
    "ReplySegment",
    "JsonSegment",
    "VideoSegment",
    "MfaceSegment",
    "LocationSegment",
    "MessageType",
    "Segment",
]
