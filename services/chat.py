from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from typing import List, Dict
import os
from dotenv import load_dotenv

load_dotenv()

class ChatService:
    def __init__(self):
        self.llm = ChatOpenAI(
            temperature=0.7,
            model_name="gpt-3.5-turbo",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.system_prompt = """You are a helpful AI assistant that provides accurate, 
        informative, and engaging responses. Always strive to give detailed explanations 
        and cite sources when possible."""
    
    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        # Convert the messages to LangChain format
        langchain_messages = [
            SystemMessage(content=self.system_prompt)
        ]
        
        for msg in messages:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))
        
        # Generate response
        response = self.llm.predict_messages(langchain_messages)
        return response.content
    
    async def create_chat_title(self, first_message: str) -> str:
        """Generate a title for a new chat based on the first message"""
        prompt = f"Generate a short, concise title (max 6 words) for a chat that starts with: {first_message}"
        messages = [
            SystemMessage(content="You are a helpful assistant that generates short, concise chat titles."),
            HumanMessage(content=prompt)
        ]
        response = self.llm.predict_messages(messages)
        return response.content.strip('"') 