import os
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


class FastRAG:
    def __init__(self, cleaned_folder="data/cleaned_files"):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.text = ""

        # Load all your cleaned files
        for file in Path(cleaned_folder).glob("*_cleaned.txt"):
            self.text += f"\n\n--- {file.name} ---\n"
            self.text += file.read_text(encoding='utf-8')

    def ask(self, question):
        response = self.client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "Business consultant. Answer from documents only."},
                {"role": "user", "content": f"Documents:\n{self.text}\n\nQuestion: {question}"}
            ]
        )
        return response.choices[0].message.content

