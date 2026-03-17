"""Chat route – accepts a query and returns a grounded AI answer."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.providers.embeddings.gemini_embeddings import GeminiEmbeddingProvider
from app.providers.llm.gemini_provider import GeminiLLMProvider
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.query_service import QueryService
from app.services.retrieval_service import RetrievalService

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask a question",
    description="Classify the query, perform hybrid retrieval, rerank, and generate a grounded answer via the LLM.",
)
async def chat(
    body: ChatRequest,
    session: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Perform retrieval-augmented generation for the user's query."""
    llm = GeminiLLMProvider()
    embeddings = GeminiEmbeddingProvider()
    retrieval = RetrievalService(session=session, embeddings=embeddings)
    query_svc = QueryService(llm=llm, retrieval=retrieval, session=session)

    result = await query_svc.answer_query(body.query)

    return ChatResponse(**result)
