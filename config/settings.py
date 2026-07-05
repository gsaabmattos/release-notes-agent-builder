from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Jira
    jira_url: str
    jira_email: str
    jira_api_token: str
    jira_project_key: str = "AP"

    # Outline
    outline_url: str
    outline_api_token: str
    outline_collection_id: str

    # Agente
    log_level: str = "INFO"
    state_dir: str = "./state"
    output_dir: str = "./output"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
