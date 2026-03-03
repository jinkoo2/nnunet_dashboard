from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "nnUNet Dashboard"
    LOG_LEVEL: str = "DEBUG"

    # Auth
    API_KEY: str = "changeme"
    DASHBOARD_USER: str = "admin"
    DASHBOARD_PASSWORD: str = "admin"

    # Storage
    DATA_DIR: str = "/app/data"
    DB_PATH: str = "/app/data/dashboard.db"

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


settings = Settings()
