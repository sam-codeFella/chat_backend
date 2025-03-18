from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from services.chat import ChatService
from services.auth import get_current_user
from sqlalchemy.orm import Session
from database.models import Chat, Message, User
from database.db import get_db

router = APIRouter()
chat_service = ChatService()

class MessageCreate(BaseModel):
    content: str
    role: str = "user"

class MessageResponse(BaseModel):
    id: int
    content: str
    role: str
    created_at: datetime

class ChatResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    messages: List[MessageResponse]

@router.post("/chats", response_model=ChatResponse)
async def create_chat(
    message: MessageCreate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Create new chat
    chat_title = await chat_service.create_chat_title(message.content)
    chat = Chat(title=chat_title, user_id=current_user.id)
    db.add(chat)
    db.commit()
    
    # Add initial message
    user_message = Message(
        content=message.content,
        role="user",
        chat_id=chat.id,
        user_id=current_user.id
    )
    db.add(user_message)
    
    # Generate AI response
    ai_response = await chat_service.generate_response([{"role": "user", "content": message.content}])
    ai_message = Message(
        content=ai_response,
        role="assistant",
        chat_id=chat.id,
        user_id=current_user.id
    )
    db.add(ai_message)
    db.commit()
    
    return ChatResponse(
        id=chat.id,
        title=chat.title,
        created_at=chat.created_at,
        messages=[
            MessageResponse(
                id=user_message.id,
                content=user_message.content,
                role=user_message.role,
                created_at=user_message.created_at
            ),
            MessageResponse(
                id=ai_message.id,
                content=ai_message.content,
                role=ai_message.role,
                created_at=ai_message.created_at
            )
        ]
    )

@router.post("/chats/{chat_id}/messages", response_model=MessageResponse)
async def create_message(
    chat_id: int,
    message: MessageCreate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get chat history
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this chat")
    
    # Add user message
    user_message = Message(
        content=message.content,
        role="user",
        chat_id=chat_id,
        user_id=current_user.id
    )
    db.add(user_message)
    db.commit()
    
    # Get chat history for context
    chat_history = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at).all()
    messages_for_ai = [{"role": msg.role, "content": msg.content} for msg in chat_history]
    
    # Generate AI response
    ai_response = await chat_service.generate_response(messages_for_ai)
    ai_message = Message(
        content=ai_response,
        role="assistant",
        chat_id=chat_id,
        user_id=current_user.id
    )
    db.add(ai_message)
    db.commit()
    
    return MessageResponse(
        id=ai_message.id,
        content=ai_message.content,
        role=ai_message.role,
        created_at=ai_message.created_at
    )

@router.get("/chats", response_model=List[ChatResponse])
async def get_chats(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chats = db.query(Chat).filter(Chat.user_id == current_user.id).all()
    return [
        ChatResponse(
            id=chat.id,
            title=chat.title,
            created_at=chat.created_at,
            messages=[
                MessageResponse(
                    id=msg.id,
                    content=msg.content,
                    role=msg.role,
                    created_at=msg.created_at
                ) for msg in chat.messages
            ]
        ) for chat in chats
    ]

@router.get("/chats/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: int,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    return ChatResponse(
        id=chat.id,
        title=chat.title,
        created_at=chat.created_at,
        messages=[
            MessageResponse(
                id=msg.id,
                content=msg.content,
                role=msg.role,
                created_at=msg.created_at
            ) for msg in chat.messages
        ]
    ) 