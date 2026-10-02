import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "AI Debate System"
    app_title: str = "Enterprise Debate Studio"
    version: str = "1.1.0"
    model_name: str = os.getenv("OLLAMA_MODEL", "phi3:mini")
    default_rounds: int = int(os.getenv("DEBATE_DEFAULT_ROUNDS", "2"))
    min_rounds: int = 1
    max_rounds: int = 10


config = AppConfig()
