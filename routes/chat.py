from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from services.chat import ChatService
from services.auth import get_current_user
from sqlalchemy.orm import Session
from database.models import Chat, Message, User
from database.db import get_db
from uuid import UUID

router = APIRouter()
chat_service = ChatService()



class MessageCreate(BaseModel):
    content: str
    role: str = "user"
    id: UUID

class ChatCreate(BaseModel):
    message: MessageCreate
    id: UUID

class MessageResponse(BaseModel):
    id: UUID
    content: str
    role: str
    created_at: datetime

class ChatResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    messages: List[MessageResponse]

# Create chat function.
@router.post("/chats", response_model=ChatResponse)
async def create_chat(
    new_chat: ChatCreate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Create new chat
    print(new_chat.message.content)
    print(new_chat.id)
    chat_title = await chat_service.create_chat_title(new_chat.message.content)
    chat = Chat(id=new_chat.id, title=chat_title, user_id=current_user.id)
    db.add(chat)
    db.commit()
    
    # Add initial message
    # the UUID is obtained from the request at the moment. -> mandatory to be achieved from the api call only.
    user_message = Message(
        id = new_chat.message.id,
        content=new_chat.message.content,
        role="user",
        chat_id=chat.id,
        user_id=current_user.id
    )
    db.add(user_message)
    
    # Generate AI response
    ai_response = await chat_service.generate_response([{"role": "user", "content": new_chat.message.content}])
    
    # yeah see here it was able to create the message UUID by itself.

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
    chat_id: UUID,
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
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
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
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