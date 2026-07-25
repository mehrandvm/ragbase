import os
from pathlib import Path
from typing import List

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
)

from app.core.vectorstore import get_vectorstore
from app.config import settings

LOADERS = {
    ".pdf":  PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".txt":  TextLoader,
    ".md":   TextLoader,
}


def load_file(file_path: str) -> List[Document]:
    ext = Path(file_path).suffix.lower()
    loader_cls = LOADERS.get(ext)
    if not loader_cls:
        raise ValueError(f"Unsupported file type: {ext}")
    return loader_cls(file_path).load()


def chunk_documents(docs: List[Document]) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        add_start_index=True,          # stores char offset in metadata
    )
    return splitter.split_documents(docs)


def tag_metadata(docs: List[Document], kb_id: str, file_name: str) -> List[Document]:
    """Attach kb_id + source filename to every chunk for citation retrieval."""
    for doc in docs:
        doc.metadata["kb_id"] = kb_id
        doc.metadata["source"] = file_name
        # PyPDFLoader already sets metadata["page"] — we leave it intact
    return docs


def ingest(file_path: str, kb_id: str, file_name: str) -> int:
    docs   = load_file(file_path)
    docs   = tag_metadata(docs, kb_id, file_name)
    chunks = chunk_documents(docs)

    store = get_vectorstore(kb_id)
    store.add_documents(chunks)

    # clean up temp upload
    os.remove(file_path)

    return len(chunks)