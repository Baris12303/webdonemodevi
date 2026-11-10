from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from app.dal.menu_dal import MenuDAL
from app.dal.review_dal import ReviewDAL
from app.redis_client import invalidate_menu_cache


class ReviewService:
    @staticmethod
    def get_menu_reviews(menu_id: int) -> List[Dict[str, Any]]:
        return ReviewDAL.get_menu_reviews(menu_id)

    @staticmethod
    def add_review(kullanici_id: int, menu_id: int, puan: int, yorum: Optional[str]) -> Dict[str, Any]:
        try:
            rev_id = ReviewDAL.add_review(kullanici_id, menu_id, puan, yorum)
            coords = MenuDAL.get_menu_cache_coords(menu_id)
            if coords:
                tarih_str = coords["tarih"].isoformat() if hasattr(coords["tarih"], "isoformat") else str(coords["tarih"])
                invalidate_menu_cache(coords["yemekhane_id"], tarih_str, coords["ogun_id"])
            return {"message": "Değerlendirmeniz başarıyla kaydedildi.", "degerlendirme_id": rev_id}
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
