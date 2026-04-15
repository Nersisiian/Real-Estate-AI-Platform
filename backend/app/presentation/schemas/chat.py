from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID


class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    session_id: Optional[UUID] = None
    user_id: Optional[str] = None
    stream: bool = False


class ChatResponse(BaseModel):
    response: str
    session_id: UUID
    context_used: List[Dict[str, Any]] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)