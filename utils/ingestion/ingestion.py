import os
from dotenv import load_dotenv

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from langchain_community.document_loaders import PyPDFLoader

"""
1. Definign custom imports. 
"""

load_dotenv()
"""
1. Load 
2. Split
3. Embed
4. Store 
"""

# even if gemini can intake 1 million tokens -> doesn't mean we send that mich.
# rule of thumb for LLM's -> Garbage in & Garbage out.
if __name__ == "__main__":
    print("hello")

    loader = PyPDFLoader




    loader = TextLoader("/Users/shams/Desktop/Panache/Udemy/saif/medium_blog_1.txt")
    document = loader.load() # this object contains 2 main fields , metadata & page_content.
    # one can also add custom metadata to denote where this information is further coming from.

    print("splitting.......")
    # there are various mechanics on how big the context window needs to be.
    # ideal practise is to have it less than token_window. (1 windows should have couple of chunks)
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)

    texts = text_splitter.split_documents(document)
    print(f"created {len(texts)} chunks")

    print("Creating embeddings......")

    embeddings = OpenAIEmbeddings(openai_api_key=os.environ.get("OPENAI_API_KEY"))

    print("ingesting......")
    PineconeVectorStore.from_documents(texts, embeddings,index_name=os.environ.get('INDEX_NAME'))
    print("finish")

