# backend/app/api/routes/kb.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.registry import create_kb, list_kbs, get_kb, delete_kb
from app.core.vectorstore import get_vectorstore

router = APIRouter(prefix="/kb", tags=["knowledge-bases"])


class KBCreateRequest(BaseModel):
    name:        str
    description: Optional[str] = None


@router.post("", status_code=201)
def create(body: KBCreateRequest):
    kb = create_kb(name=body.name, description=body.description)
    return kb


@router.get("")
def list_all():
    return list_kbs()


@router.get("/{kb_id}")
def get_one(kb_id: str):
    kb = get_kb(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


@router.delete("/{kb_id}", status_code=204)
def delete(kb_id: str):
    if not get_kb(kb_id):
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # delete vectors from Chroma
    store = get_vectorstore(kb_id)
    store.delete_collection()

    # remove from registry
    delete_kb(kb_id)


# Three endpoints — create, list, delete.
# Delete does two things in order: wipes the Chroma collection (vectors on disk),
# then removes the entry from the JSON registry. Order matters — if registry deletion
# ran first and Chroma deletion failed you'd have orphaned vectors with no pointer.
# get_one exists mainly for the frontend to validate a kb_id before rendering the chat page.