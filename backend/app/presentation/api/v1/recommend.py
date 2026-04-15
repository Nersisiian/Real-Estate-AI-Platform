from fastapi import APIRouter, Depends, HTTPException
from typing import List
from uuid import UUID

from app.presentation.schemas.property import PropertyResponse
from app.application.services.recommend_use_case import RecommendUseCase
from app.core.dependencies import get_recommend_use_case

router = APIRouter()


@router.get("/recommend/{property_id}/similar", response_model=List[PropertyResponse])
async def get_similar_properties(
    property_id: UUID,
    limit: int = 5,
    recommend_use_case: RecommendUseCase = Depends(get_recommend_use_case),
):
    try:
        similar = await recommend_use_case.find_similar(property_id, limit)
        return [PropertyResponse.model_validate(p) for p in similar]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend/personalized", response_model=List[PropertyResponse])
async def personalized_recommendations(
    user_preferences: dict,
    limit: int = 10,
    recommend_use_case: RecommendUseCase = Depends(get_recommend_use_case),
):
    try:
        recommendations = await recommend_use_case.personalized_recommend(
            user_preferences, limit
        )
        return [PropertyResponse.model_validate(p) for p in recommendations]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
