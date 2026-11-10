from typing import List
from fastapi import APIRouter, Depends
from app.schemas.review import ReviewCreateRequest, ReviewOut
from app.services.auth_service import get_current_user
from app.services.review_service import ReviewService

router = APIRouter(prefix="/api/reviews", tags=["Değerlendirmeler"])


@router.get("/{menu_id}", response_model=List[ReviewOut], summary="Menü Değerlendirmelerini Getir")
def get_reviews(menu_id: int):
    return ReviewService.get_menu_reviews(menu_id)


@router.post("", summary="Menüye Puan ve Yorum Yap")
def add_review(req: ReviewCreateRequest, user: dict = Depends(get_current_user)):
    return ReviewService.add_review(user["id"], req.menu_id, req.puan, req.yorum)
