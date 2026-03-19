from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/churn_db"
    MODEL_VERSION: str = "v1.0"
    ENV: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
