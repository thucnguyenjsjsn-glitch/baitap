import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

@dataclass(frozen=True)
class Settings:
    database_url: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-5-mini"
    ai_mode: str = "mock"

def get_settings() -> Settings:
    return Settings(database_url=os.getenv('DATABASE_URL',''), openai_api_key=os.getenv('OPENAI_API_KEY',''), openai_model=os.getenv('OPENAI_MODEL','gpt-5-mini'), ai_mode=os.getenv('AI_MODE','mock'))
