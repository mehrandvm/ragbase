# backend/app/core/graph.py
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import json
from typing import TypedDict, List, AsyncGenerator

from langchain.schema import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END

from app.core.vectorstore import get_vectorstore
from app.config import settings


# ── State ──────────────────────────────────────────────────────────────────────

class GraphState(TypedDict):
    question:                str
    chat_history:            List[dict]
    contextualized_question: str
    documents:               List[Document]
    generation:              str
    rewrite_count:           int


# ── Grader schema ──────────────────────────────────────────────────────────────

class GradeDoc(BaseModel):
    relevant: bool = Field(description="True if doc is relevant to the question")


# ── Prompts (module-level is fine — no API calls happen here) ──────────────────

CONTEXTUALIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Rewrite the user's question to be fully standalone given the chat history. "
     "If already standalone, return it as-is. Return ONLY the question."),
    MessagesPlaceholder("chat_history"),
    ("human", "{question}"),
])

GRADE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Grade whether the document is relevant to the question. "
     "Be lenient — partial relevance counts."),
    ("human", "Document:\n{document}\n\nQuestion: {question}"),
])

REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Retrieved documents were not relevant. Rewrite the question with different "
     "keywords to improve retrieval. Return ONLY the rewritten question."),
    ("human", "Original question: {question}"),
])

GENERATE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Answer using ONLY the provided context. "
     "If context is insufficient, say so. "
     "End your answer listing sources as: [Source: filename, page X]"),
    ("human", "Context:\n{context}\n\nQuestion: {question}"),
])


# ── Pure helpers (no LLM needed) ───────────────────────────────────────────────

def format_history(chat_history: List[dict]) -> list:
    out = []
    for msg in chat_history:
        cls = HumanMessage if msg["role"] == "human" else AIMessage
        out.append(cls(content=msg["content"]))
    return out


def format_context(docs: List[Document]) -> str:
    parts = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        page   = doc.metadata.get("page", "")
        label  = f"[Source: {source}, page {page}]" if page != "" else f"[Source: {source}]"
        parts.append(f"{label}\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


# ── Graph builder ──────────────────────────────────────────────────────────────

MAX_REWRITES = 2


def build_graph(kb_id: str):
    # instantiated here — deferred until first actual request, not at import time
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=settings.openai_api_key,
    )
    llm_grader = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=settings.openai_api_key,
    )

    # ── Nodes ────────────────────────────────────────────────────────────────

    def contextualize_query(state: GraphState) -> dict:
        history = format_history(state["chat_history"])
        if not history:
            return {"contextualized_question": state["question"]}
        chain  = CONTEXTUALIZE_PROMPT | llm | StrOutputParser()
        result = chain.invoke({"chat_history": history, "question": state["question"]})
        return {"contextualized_question": result}

    def retrieve(state: GraphState) -> dict:
        store = get_vectorstore(kb_id)
        docs  = store.similarity_search(state["contextualized_question"], k=settings.top_k)
        return {"documents": docs}

    def grade_documents(state: GraphState) -> dict:
        grader   = GRADE_PROMPT | llm_grader.with_structured_output(GradeDoc)
        relevant = []
        for doc in state["documents"]:
            score = grader.invoke({
                "document": doc.page_content,
                "question": state["contextualized_question"],
            })
            if score.relevant:
                relevant.append(doc)
        return {"documents": relevant}

    def rewrite_query(state: GraphState) -> dict:
        chain     = REWRITE_PROMPT | llm | StrOutputParser()
        rewritten = chain.invoke({"question": state["contextualized_question"]})
        return {
            "contextualized_question": rewritten,
            "rewrite_count":           state.get("rewrite_count", 0) + 1,
        }

    def generate(state: GraphState) -> dict:
        chain  = GENERATE_PROMPT | llm | StrOutputParser()
        answer = chain.invoke({
            "context":  format_context(state["documents"]),
            "question": state["contextualized_question"],
        })
        return {"generation": answer}

    # ── Conditional edge ──────────────────────────────────────────────────────

    def route_after_grading(state: GraphState) -> str:
        if state["documents"]:
            return "generate"
        if state.get("rewrite_count", 0) >= MAX_REWRITES:
            return "generate"
        return "rewrite_query"

    # ── Assemble ──────────────────────────────────────────────────────────────

    g = StateGraph(GraphState)

    g.add_node("contextualize_query", contextualize_query)
    g.add_node("retrieve",            retrieve)
    g.add_node("grade_documents",     grade_documents)
    g.add_node("rewrite_query",       rewrite_query)
    g.add_node("generate",            generate)

    g.add_edge(START,                 "contextualize_query")
    g.add_edge("contextualize_query", "retrieve")
    g.add_edge("retrieve",            "grade_documents")
    g.add_edge("rewrite_query",       "retrieve")
    g.add_edge("generate",            END)

    g.add_conditional_edges(
        "grade_documents",
        route_after_grading,
        {"generate": "generate", "rewrite_query": "rewrite_query"},
    )

    return g.compile()


# ── Public interface ───────────────────────────────────────────────────────────

def _initial_state(question: str, chat_history: List[dict]) -> GraphState:
    return {
        "question":                question,
        "chat_history":            chat_history,
        "contextualized_question": "",
        "documents":               [],
        "generation":              "",
        "rewrite_count":           0,
    }


async def run_query(kb_id: str, question: str, chat_history: List[dict]) -> dict:
    """Non-streaming. Returns full answer + source documents."""
    graph  = build_graph(kb_id)
    result = await graph.ainvoke(_initial_state(question, chat_history))
    return {"answer": result["generation"], "documents": result["documents"]}


async def stream_query(kb_id: str, question: str, chat_history: List[dict]) -> AsyncGenerator:
    """Yields text tokens during generation, then a citations dict at the end."""
    graph      = build_graph(kb_id)
    final_docs = []

    async for event in graph.astream_events(_initial_state(question, chat_history), version="v2"):

        # capture graded docs once grading node finishes
        if (
            event["event"] == "on_chain_end"
            and event["metadata"].get("langgraph_node") == "grade_documents"
        ):
            final_docs = event["data"]["output"].get("documents", [])

        # stream tokens from generate node only
        if (
            event["event"] == "on_chat_model_stream"
            and event["metadata"].get("langgraph_node") == "generate"
        ):
            chunk = event["data"]["chunk"].content
            if chunk:
                yield chunk

    # final yield — citations for the frontend
    yield {
        "citations": [
            {
                "source": doc.metadata.get("source", "unknown"),
                "page":   doc.metadata.get("page"),
                "chunk":  doc.page_content[:300],
            }
            for doc in final_docs
        ]
    }


# All LLM-dependent nodes are inner functions inside build_graph() — they close over
# llm and llm_grader which are instantiated at call time, not import time.
# This means importing graph.py never touches the OpenAI API or reads settings,
# so startup never fails due to missing keys or network issues.
# Prompts stay at module level because they're just data structures — no API calls.