import os
from pathlib import Path
from groq import Groq
from config import Config
from src.chunk_search import ChunkSearch


def get_groq_client():
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return client

class FastRAG:
    def __init__(self):
        self.client = get_groq_client()
        self.text = ""
        project_root = Path(__file__).parent.parent
        cleaned_folder =  project_root/Config.output_dir
        # Load all your cleaned files
        for file in Path(cleaned_folder).glob("*_cleaned.txt"):
            self.text += f"\n\n--- {file.name} ---\n"
            self.text += file.read_text(encoding='utf-8')




    def ask(self, question):

        relevant_chunks = ChunkSearch(self.text).find_relevant(question)
        context = "\n\n".join([chunk['text'] for chunk in relevant_chunks])

        if not context:
            return "❌ No relevant information found in the documents."

        response = self.client.chat.completions.create(
            model=Config.MODEL_NAME,
            messages=[
                {"role": "system", "content": "Business consultant. Answer from documents only."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
            ]
        )
        return response.choices[0].message.content

