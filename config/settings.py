from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Jira
    jira_url: str
    jira_email: str
    jira_api_token: str
    jira_project_key: str = "AP"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_temperature: float = 0.1
    ollama_top_p: float = 0.8
    ollama_repeat_penalty: float = 1.2

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
