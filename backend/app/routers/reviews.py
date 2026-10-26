from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.review import ReviewCreateRequest, ReviewOut
from app.dal.review_dal import ReviewDAL
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/reviews", tags=["Değerlendirmeler"])

@router.get("/{menu_id}", response_model=List[ReviewOut], summary="Menü Değerlendirmelerini Getir")
def get_reviews(menu_id: int):
    return ReviewDAL.get_menu_reviews(menu_id)

@router.post("", summary="Menüye Puan ve Yorum Yap")
def add_review(req: ReviewCreateRequest, user: dict = Depends(get_current_user)):
    try:
        rev_id = ReviewDAL.add_review(user["id"], req.menu_id, req.puan, req.yorum)
        return {"message": "Değerlendirmeniz başarıyla kaydedildi.", "degerlendirme_id": rev_id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

