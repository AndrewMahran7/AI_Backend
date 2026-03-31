"""Pydantic schemas for conversations and messages."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Sources ──────────────────────────────────────────────────────────────

class SourceItem(BaseModel):
    record_id: str
    title: str
    source_type: str = ""
    source: str = ""
    preview_text: str = ""


# ── Messages ─────────────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class MessageOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    sources: list[SourceItem] = Field(default_factory=list)
    confidence: float | None = None
    notes: str = ""
    query_type: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Conversations ────────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    title: str = Field(default="New Chat", max_length=512)


class ConversationOut(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = Field(default_factory=list)


# ── Send message response ───────────────────────────────────────────────

class SendMessageResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
