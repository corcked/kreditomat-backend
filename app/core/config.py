from typing import Optional, List
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, RedisDsn


class Settings(BaseSettings):
    # Application
    PROJECT_NAME: str = "Kreditomat API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="dev", pattern="^(dev|staging|prod)$")
    DEBUG: bool = Field(default=True)
    
    # Database
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql://postgres:postgres@localhost:5432/kreditomat"
    )
    DB_ECHO: bool = Field(default=False)
    
    # Redis
    REDIS_URL: RedisDsn = Field(
        default="redis://localhost:6379/0"
    )
    
    # JWT
    JWT_SECRET_KEY: str = Field(default="your-secret-key-here")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440)  # 24 hours
    
    # Telegram Gateway
    TELEGRAM_GATEWAY_TOKEN: str = Field(default="")
    TELEGRAM_GATEWAY_URL: str = Field(
        default="https://gateway.telegram.org"
    )
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"]
    )
    
    # Security
    SECRET_KEY: str = Field(default="your-app-secret-key")
    
    # External APIs
    GEOIP_API_KEY: Optional[str] = Field(default=None)
    
    # Limits
    MAX_LOAN_AMOUNT: int = Field(default=100_000_000)  # 100 million sum
    MIN_LOAN_AMOUNT: int = Field(default=1)
    MAX_LOAN_TERM_MONTHS: int = Field(default=36)
    MIN_LOAN_TERM_MONTHS: int = Field(default=1)
    MAX_PDN_RATIO: float = Field(default=50.0)  # 50%
    
    # OTP
    OTP_TTL_SECONDS: int = Field(default=300)  # 5 minutes
    OTP_LENGTH: int = Field(default=6)
    
    # Session
    SESSION_TTL_SECONDS: int = Field(default=86400)  # 24 hours
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic"""
        return str(self.DATABASE_URL).replace("postgresql+asyncpg://", "postgresql://")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()