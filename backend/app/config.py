import os

class Settings:
    # Primary DB (Yazma işlemleri & Stored Procedure'ler)
    DB_PRIMARY_HOST: str = os.getenv("DB_PRIMARY_HOST", "mysql-primary")
    DB_PRIMARY_PORT: int = int(os.getenv("DB_PRIMARY_PORT", "3306"))
    
    # Replica DB (Okuma işlemleri & View'lar)
    DB_REPLICA_HOST: str = os.getenv("DB_REPLICA_HOST", "mysql-replica")
    DB_REPLICA_PORT: int = int(os.getenv("DB_REPLICA_PORT", "3306"))
    
    # DB Kimlik Bilgileri
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "rootpass")
    DB_NAME: str = os.getenv("DB_NAME", "yemekhane_db")
    
    # Redis (Önbellek & Oturum)
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    
    # Oturum Süresi (30 Dakika = 1800 saniye)
    SESSION_EXPIRE_SECONDS: int = 1800

settings = Settings()

