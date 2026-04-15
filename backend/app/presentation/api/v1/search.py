from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from decimal import Decimal

from app.presentation.schemas.property import (
    SearchRequest,
    SearchResponse,
    PropertyResponse,
)
from app.application.services.rag_service import RAGRetrievalService
from app.domain.repositories import PropertyRepository
from app.core.dependencies import get_rag_retrieval_service, get_property_repository

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    rag_service: RAGRetrievalService = Depends(get_rag_retrieval_service),
    property_repo: PropertyRepository = Depends(get_property_repository),
):
    try:
        filters = {}
        if request.filters:
            filters = {
                "city": request.filters.city,
                "min_price": request.filters.min_price,
                "max_price": request.filters.max_price,
                "min_rooms": request.filters.min_rooms,
                "max_rooms": request.filters.max_rooms,
                "property_type": request.filters.property_type,
            }

        search_results, properties = await rag_service.retrieve_context(
            query=request.query,
            top_k=request.top_k,
            filters=filters,
        )

        if len(properties) < request.top_k and request.filters:
            criteria_props = await property_repo.find_by_criteria(
                city=request.filters.city,
                min_price=(
                    Decimal(str(request.filters.min_price))
                    if request.filters.min_price
                    else None
                ),
                max_price=(
                    Decimal(str(request.filters.max_price))
                    if request.filters.max_price
                    else None
                ),
                min_rooms=request.filters.min_rooms,
                max_rooms=request.filters.max_rooms,
                property_type=request.filters.property_type,
                limit=request.top_k - len(properties),
            )
            properties.extend(criteria_props)
            seen = set()
            unique_props = []
            for p in properties:
                if p.id not in seen:
                    seen.add(p.id)
                    unique_props.append(p)
            properties = unique_props

        return SearchResponse(
            results=[PropertyResponse.model_validate(p) for p in properties],
            total=len(properties),
            query=request.query,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties", response_model=list[PropertyResponse])
async def list_properties(
    city: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_rooms: Optional[int] = Query(None),
    max_rooms: Optional[int] = Query(None),
    property_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    property_repo: PropertyRepository = Depends(get_property_repository),
):
    properties = await property_repo.find_by_criteria(
        city=city,
        min_price=Decimal(str(min_price)) if min_price else None,
        max_price=Decimal(str(max_price)) if max_price else None,
        min_rooms=min_rooms,
        max_rooms=max_rooms,
        property_type=property_type,
        limit=limit,
        offset=offset,
    )
    return [PropertyResponse.model_validate(p) for p in properties]
