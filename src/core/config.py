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
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    MODEL_NAME = os.getenv("MODEL_NAME")
    prompts_dir =  PROJECT_ROOT / os.getenv("PROMPTS_DIR","src/prompts")
    input_dir = PROJECT_ROOT / os.getenv("INPUT_DIR", "data/input_files")
    output_dir = PROJECT_ROOT / os.getenv("OUTPUT_DIR", "data/cleaned_files")
    graph_dir = PROJECT_ROOT / os.getenv("GRAPH_DIR", "data/graph")
    chroma_dir = PROJECT_ROOT / os.getenv("CHROMA_DIR", "data/chroma")
    frameworks_dir= PROJECT_ROOT / os.getenv("FRAMEWORKS_DIR", "data/frameworks")
    NEO4J_URI = os.getenv("NEO4J_URI")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
    root=PROJECT_ROOT