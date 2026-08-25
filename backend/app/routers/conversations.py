"""Conversation API route placeholders."""

from fastapi import APIRouter


router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("")
async def list_conversations() -> dict[str, str]:
    """Return the placeholder for listing conversations."""
    return {"message": "List conversations - coming in Step 4.1"}


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: int) -> dict[str, str]:
    """Return the placeholder for retrieving one conversation."""
    _ = conversation_id
    return {"message": "Get conversation - coming in Step 4.1"}


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: int) -> dict[str, str]:
    """Return the placeholder for retrieving conversation messages."""
    _ = conversation_id
    return {"message": "Get messages - coming in Step 4.1"}


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: int) -> dict[str, str]:
    """Return the placeholder for deleting one conversation."""
    _ = conversation_id
    return {"message": "Delete conversation - coming in Step 4.1"}
