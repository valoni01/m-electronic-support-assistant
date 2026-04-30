from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mcp_server_url: str
    openai_api_key: str
    llm_model: str = "gpt-4o-mini"
    app_env: str = "local"

    class Config:
        env_file = ".env"


settings = Settings()