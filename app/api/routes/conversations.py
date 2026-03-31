"""Conversation routes – CRUD for conversations and messages."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.conversation import (
    ConversationCreate,
    ConversationOut,
    MessageCreate,
    MessageOut,
    SendMessageResponse,
)
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post(
    "",
    response_model=ConversationOut,
    status_code=201,
    summary="Create a conversation",
)
async def create_conversation(
    body: ConversationCreate = ConversationCreate(),
    session: AsyncSession = Depends(get_db),
) -> ConversationOut:
    svc = ConversationService(session)
    conv = await svc.create_conversation(title=body.title)
    return ConversationOut.model_validate(conv)


@router.get(
    "",
    response_model=list[ConversationOut],
    summary="List conversations",
)
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    query: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> list[ConversationOut]:
    svc = ConversationService(session)
    convs = await svc.list_conversations(limit=limit, offset=offset, query=query)
    return [ConversationOut.model_validate(c) for c in convs]


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageOut],
    summary="Get messages for a conversation",
)
async def get_messages(
    conversation_id: uuid.UUID,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
) -> list[MessageOut]:
    svc = ConversationService(session)
    msgs = await svc.get_messages(conversation_id, limit=limit, offset=offset)
    return [MessageOut.model_validate(m) for m in msgs]


@router.delete(
    "/{conversation_id}",
    status_code=204,
    summary="Delete a conversation",
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> Response:
    svc = ConversationService(session)
    deleted = await svc.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{conversation_id}/messages",
    response_model=SendMessageResponse,
    status_code=201,
    summary="Send a message and get AI response",
)
async def send_message(
    conversation_id: uuid.UUID,
    body: MessageCreate,
    session: AsyncSession = Depends(get_db),
) -> SendMessageResponse:
    svc = ConversationService(session)
    try:
        user_msg, assistant_msg = await svc.send_message(
            conversation_id=conversation_id,
            content=body.content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return SendMessageResponse(
        user_message=MessageOut.model_validate(user_msg),
        assistant_message=MessageOut.model_validate(assistant_msg),
    )
