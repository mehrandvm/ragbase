import asyncio
from app.core.graph import run_query

async def test():
    result = await run_query(
        kb_id="test-kb",
        question="summarize the document",
        chat_history=[]
    )
    print("ANSWER:", result["answer"])
    print("\nSOURCES:")
    for doc in result["documents"]:
        print(" -", doc.metadata.get("source"), "p.", doc.metadata.get("page"))