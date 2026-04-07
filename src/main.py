from pathlib import Path

from pdf_cleaner import clean_all_pdfs
from src.rag_system import SimpleRAG


project_root = Path(__file__).parent.parent
input_dir = str(project_root / "data" / "input_files")
output_dir = str(project_root / "data" / "cleaned_files")

#cleaned_files = clean_all_pdfs(input_dir,output_dir)
# Initialize
rag = SimpleRAG(output_dir, model="llama2")

# Ask questions
answer = rag.ask("What is this document about?")
print(answer)

# Simple version without formatting
answer = rag.ask_simple("What are the key points?")
print(answer)