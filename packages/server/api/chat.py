"""Chat API endpoints with RAG."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..config import settings
from ..storage.database import Database, get_db
from ..services.chat_service import ChatService, ChatServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


# Request Models
class ChatRequest(BaseModel):
    """Request model for chat."""

    message: str = Field(..., min_length=1, max_length=4000, description="User message")
    conversation_id: str | None = Field(
        default=None,
        description="Optional conversation ID for multi-turn chat",
    )
    options: dict[str, Any] | None = Field(
        default=None,
        description="Optional settings: model, temperature, max_context",
    )


# Response Models
class ChatSource(BaseModel):
    """Source reference in chat response."""

    id: int
    title: str
    url: str | None = None
    snippet: str
    similarity: float


class ChatResponse(BaseModel):
    """Response model for chat."""

    success: bool = True
    data: dict[str, Any]


class ConversationSummary(BaseModel):
    """Summary of a conversation."""

    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class ConversationListResponse(BaseModel):
    """Response for conversation list."""

    success: bool = True
    conversations: list[ConversationSummary]
    total: int


class ConversationDetailResponse(BaseModel):
    """Response for conversation detail."""

    success: bool = True
    conversation: dict[str, Any]


def get_chat_service() -> ChatService | None:
    """Get ChatService instance if configured."""
    if not settings.openai_api_key:
        return None
    try:
        return ChatService()
    except ValueError:
        return None


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Database = Depends(get_db),
) -> ChatResponse:
    """Send a message and get AI response with RAG.

    Uses semantic search to find relevant articles from your knowledge base,
    then generates a response using the context.

    Requires:
    - OPENAI_API_KEY environment variable
    - Articles must be embedded for semantic search

    Args:
        request: Chat request with message and optional conversation_id.

    Returns:
        ChatResponse with answer, sources, and usage info.
    """
    chat_service = get_chat_service()
    if not chat_service:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "CHAT_NOT_CONFIGURED",
                "message": "Chat requires OPENAI_API_KEY to be configured",
            },
        )

    # Extract options
    options = request.options or {}
    max_context = options.get("max_context", 5)
    temperature = options.get("temperature", 0.7)
    max_tokens = options.get("max_tokens", 2000)

    try:
        result = await chat_service.chat(
            query=request.message,
            db=db,
            conversation_id=request.conversation_id,
            max_context=max_context,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return ChatResponse(
            success=True,
            data={
                "answer": result["answer"],
                "sources": result["sources"],
                "conversation_id": result["conversation_id"],
                "usage": result["usage"],
            },
        )

    except ChatServiceError as e:
        logger.error(f"Chat failed: {e.message}")
        raise HTTPException(
            status_code=400,
            detail={
                "code": e.code,
                "message": e.message,
            },
        )
    except Exception as e:
        logger.exception("Unexpected error during chat")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
            },
        )


@router.get("/history", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Database = Depends(get_db),
) -> ConversationListResponse:
    """List all chat conversations.

    Returns a paginated list of conversations with summary info.
    """
    chat_service = get_chat_service()
    if not chat_service:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "CHAT_NOT_CONFIGURED",
                "message": "Chat requires OPENAI_API_KEY to be configured",
            },
        )

    try:
        conversations = await chat_service.list_conversations(
            db=db,
            limit=limit,
            offset=offset,
        )

        # Get total count
        total_result = await db.fetchone(
            "SELECT COUNT(*) as count FROM conversations"
        )
        total = total_result["count"] if total_result else 0

        return ConversationListResponse(
            success=True,
            conversations=[
                ConversationSummary(
                    id=c["id"],
                    title=c["title"],
                    created_at=str(c["created_at"]),
                    updated_at=str(c["updated_at"]),
                    message_count=c["message_count"],
                )
                for c in conversations
            ],
            total=total,
        )

    except Exception as e:
        logger.exception("Error listing conversations")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
            },
        )


@router.get("/history/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    db: Database = Depends(get_db),
) -> ConversationDetailResponse:
    """Get a specific conversation with all messages.

    Returns the full conversation history including sources.
    """
    chat_service = get_chat_service()
    if not chat_service:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "CHAT_NOT_CONFIGURED",
                "message": "Chat requires OPENAI_API_KEY to be configured",
            },
        )

    try:
        conversation = await chat_service.get_conversation(
            db=db,
            conversation_id=conversation_id,
        )

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "CONVERSATION_NOT_FOUND",
                    "message": f"Conversation {conversation_id} not found",
                },
            )

        return ConversationDetailResponse(
            success=True,
            conversation=conversation,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting conversation")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
            },
        )


@router.delete("/history/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Delete a conversation and all its messages.

    This action cannot be undone.
    """
    chat_service = get_chat_service()
    if not chat_service:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "CHAT_NOT_CONFIGURED",
                "message": "Chat requires OPENAI_API_KEY to be configured",
            },
        )

    try:
        deleted = await chat_service.delete_conversation(
            db=db,
            conversation_id=conversation_id,
        )

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "CONVERSATION_NOT_FOUND",
                    "message": f"Conversation {conversation_id} not found",
                },
            )

        return {
            "success": True,
            "message": "Conversation deleted",
            "conversation_id": conversation_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error deleting conversation")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
            },
        )
