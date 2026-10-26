from typing import Optional, Dict, Any, List
from datetime import date, timedelta
from app.dal.menu_dal import MenuDAL
from app.redis_client import get_cached_menu, set_cached_menu

class MenuService:
    @staticmethod
    def get_daily_menu(yemekhane_id: int, tarih: date, ogun_id: int) -> Optional[Dict[str, Any]]:
        tarih_str = tarih.isoformat()
        
        # 1. Önce Redis Önbelleğine Bak
        cached = get_cached_menu(yemekhane_id, tarih_str, ogun_id)
        if cached:
            cached["kaynak"] = "cache"
            return cached

        # 2. Önbellekte yoksa Replica DB'den View sorgusu yap
        menu = MenuDAL.get_menu_detail(yemekhane_id, tarih, ogun_id)
        if menu:
            menu["kaynak"] = "database"
            # Redis'e gün sonuna kadar kaydet
            set_cached_menu(yemekhane_id, tarih_str, ogun_id, menu)
            return menu
            
        return None

    @staticmethod
    def get_weekly_menus(yemekhane_id: int, baslangic_tarihi: Optional[date] = None) -> List[Dict[str, Any]]:
        if not baslangic_tarihi:
            baslangic_tarihi = date.today()
        bitis_tarihi = baslangic_tarihi + timedelta(days=6)
        return MenuDAL.get_weekly_menus(yemekhane_id, baslangic_tarihi, bitis_tarihi)

