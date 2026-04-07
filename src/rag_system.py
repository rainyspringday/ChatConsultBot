import os
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
from langchain_community.callbacks.fiddler_callback import MODEL_NAME

load_dotenv()
load_dotenv('.env.example')


def get_groq_client():
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return client

class FastRAG:
    def __init__(self, cleaned_folder="data/cleaned_files"):
        self.client = get_groq_client()
        self.text = ""

        # Load all your cleaned files
        for file in Path(cleaned_folder).glob("*_cleaned.txt"):
            self.text += f"\n\n--- {file.name} ---\n"
            self.text += file.read_text(encoding='utf-8')

    def ask(self, question):
        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Business consultant. Answer from documents only."},
                {"role": "user", "content": f"Documents:\n{self.text}\n\nQuestion: {question}"}
            ]
        )
        return response.choices[0].message.content

