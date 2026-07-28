from typing import List
from langchain.schema import Document
from sentence_transformers import CrossEncoder
from app.config import settings

_reranker = None


def get_reranker() -> CrossEncoder:
    # lazy singleton — model downloads on first call, cached after
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(settings.hf_reranker_model)
    return _reranker


def rerank(docs: List[Document], question: str) -> List[Document]:
    if not docs:
        return docs

    reranker = get_reranker()
    pairs    = [(question, doc.page_content) for doc in docs]
    scores   = reranker.predict(pairs)

    # sort by score descending, tag score on metadata for debugging
    scored = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
    for score, doc in scored:
        doc.metadata["rerank_score"] = round(float(score), 4)

    # filter by threshold — fall back to top 3 if all score below it
    relevant = [doc for score, doc in scored if score > settings.reranker_threshold]
    return relevant if relevant else [doc for _, doc in scored[:3]]


# Lazy singleton CrossEncoder — model is downloaded from HuggingFace Hub on first
# call and cached locally (~80MB). Subsequent calls reuse the loaded model.
# rerank() scores every (question, chunk) pair, sorts by score, filters by threshold.
# The fallback to top-3 ensures the generate node always has something to work with
# even when the document set is genuinely weak.