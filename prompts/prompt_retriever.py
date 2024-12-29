from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import json

load_dotenv()

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstores = {
    "planner": PineconeVectorStore(index_name="aicfo-planner", embedding=embeddings),
    "trsc_nl2sql": PineconeVectorStore(
        index_name="aicfo-transaction-nl2sql", embedding=embeddings
    ),
}


def shots_retriever(task: str, node, k: int = 8) -> str:

    retriever = vectorstores[node].as_retriever(search_kwargs={"k": k})
    docs = retriever.invoke(task)
    shots = ""

    if node == "planner":
        for doc in docs:
            text = doc.page_content
            plan = doc.metadata["plan"]
            shots += f"Task:{text}\n{plan}\n"
    if node == "trsc_nl2sql":
        for doc in docs:
            text = doc.page_content
            plan = doc.metadata["SQL"]
            shots += f"질문:{text}\nSQL:{plan}\n"
    return shots
