import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent

env=PROJECT_ROOT / '.env'
env_example=PROJECT_ROOT / '.env.example'

load_dotenv(env)
load_dotenv(env_example)


class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    MODEL_NAME = os.getenv("MODEL_NAME")
    input_dir = os.getenv("INPUT_DIR", "../../data/input_files")
    output_dir = os.getenv("OUTPUT_DIR", "../../data/cleaned_files")