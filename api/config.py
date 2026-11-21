import os


class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kitchen_vision.db")
    API_KEY = os.getenv("API_KEY", "dev-key")
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
    TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", "900"))
    EVIDENCE_URL_TTL_SECONDS = int(os.getenv("EVIDENCE_URL_TTL_SECONDS", "300"))


settings = Settings()
