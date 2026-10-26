import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, menus, reservations, balance, reviews, admin

# Log yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("app")

app = FastAPI(
    title="Kampüs Yemekhane Otomasyonu API",
    version="1.0.0",
    description="Mikroservis Mimarisine Sahip Kampüs Yemekhane Yönetim Sistemi REST API",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# CORS Middleware (Apache üzerinden veya doğrudan erişim için)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router'ları ekle
app.include_router(auth.router)
app.include_router(menus.router)
app.include_router(reservations.router)
app.include_router(balance.router)
app.include_router(reviews.router)
app.include_router(admin.router)

@app.get("/api/health", tags=["Sağlık"])
def health_check():
    return {"status": "ok", "service": "yemekhane-backend"}

