from src.rag_system import FastRAG

#cleaned_files = clean_all_pdfs()

rag=FastRAG()
response=rag.ask("What format should I use if I want to make a printed, physical copy of my book?")
print(response)