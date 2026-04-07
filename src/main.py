from pathlib import Path

from pdf_cleaner import clean_all_pdfs
from src.rag_system import FastRAG

cleaned_files = clean_all_pdfs()