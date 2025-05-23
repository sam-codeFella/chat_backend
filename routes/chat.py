from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from services.chat import ChatService
from services.auth import get_current_user
from sqlalchemy.orm import Session
from database.models import Chat, Message, User, Vote
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

class VoteResponse(BaseModel):
    id: str
    chat_id: UUID
    message_id: UUID
    type: str
    created_at: datetime

class VoteUpdateRequest(BaseModel):
    type: str

# Create chat function.
# This is a function to retrieve in case of new chat's & it's subsequent interactions are maintained here only.
# The other calls are used to populate the frontend chat history & everything.
# I am writing this very poorly - rewrite & rethink this.
# it will maintain context & be rendered.
@router.post("/chats", response_model=ChatResponse)
async def create_chat(
    chat: ChatCreate,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chat_id = chat.id
    message_id = chat.message.id
    chat_created_at = None
    chat_title = None

    existing_chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()

    if existing_chat:
        chat_created_at = existing_chat.created_at
        chat_title = existing_chat.title
    else:
        chat_title = await chat_service.create_chat_title(chat.message.content)
        # is the chatDTO required outside this scope ?
        chatDTO = Chat(id=chat.id, title=chat_title, user_id=current_user.id)
        db.add(chatDTO)
        db.commit()
        chat_created_at = chatDTO.created_at

    
    # Add initial message
    # the UUID is obtained from the request at the moment. -> mandatory to be achieved from the api call only.
    # every message is also saved here.
    user_message = Message(
        id = message_id,
        content=chat.message.content,
        role="user",
        chat_id=chat_id,
        user_id=current_user.id
    )
    db.add(user_message)
    
    # Generate AI response
    ai_response = await chat_service.generate_response([{"role": "user", "content": chat.message.content}])

    # yeah see here it was able to create the message UUID by itself.

    ai_message = Message(
        content=ai_response,
        role="assistant",
        chat_id=chat_id,
        user_id=current_user.id
    )
    db.add(ai_message)
    db.commit()

    # due to my bad implementation above. this is suffering.
    # You know the fuck up. -> Fixed it by extracting the return object fields.

    # why  does the return consist the entire list ? - This is a bit of heavy packet size.
    # let's see how we can do better at this.
    # client disconnectivity may be the main reason.
    return ChatResponse(
        id=chat_id,
        title=chat_title,
        created_at=chat_created_at,
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

@router.get("/chats/{chat_id}/votes", response_model=List[VoteResponse])
async def get_votes_by_chat_id(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if chat exists and user has access
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this chat")
    
    # Get all votes for the chat
    votes = db.query(Vote).filter(Vote.chat_id == str(chat_id)).all()
    
    return [
        VoteResponse(
            id=vote.id,
            chat_id=vote.chat_id,
            message_id=vote.message_id,
            type=vote.type,
            created_at=vote.created_at
        ) for vote in votes
    ]

@router.put("/chats/{chat_id}/messages/{message_id}/vote", response_model=VoteResponse)
async def update_vote(
    chat_id: UUID,
    message_id: UUID,
    vote_update: VoteUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if chat exists and user has access
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    if chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this chat")
    
    # Check if message exists in the chat
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.chat_id == chat_id
    ).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found in this chat")
    
    # Find existing vote or create new one
    vote = db.query(Vote).filter(
        Vote.chat_id == str(chat_id),
        Vote.message_id == str(message_id)
    ).first()
    
    if vote:
        # Update existing vote
        vote.type = vote_update.type
    else:
        # Create new vote
        vote = Vote(
            chat_id=str(chat_id),
            message_id=str(message_id),
            type=vote_update.type
        )
        db.add(vote)
    
    db.commit()
    db.refresh(vote)

    # what's happening here ?
    return VoteResponse(
        id=vote.id,
        chat_id=vote.chat_id,
        message_id=vote.message_id,
        type=vote.type,
        created_at=vote.created_at
    )