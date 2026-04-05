import re
import unicodedata
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader


def clean_text(text):
    # Normalize unicode
    text = unicodedata.normalize('NFKD', text)

    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # Fix hyphenated words broken across lines
    text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)

    # Remove page numbers
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Page \d+', '', text, flags=re.IGNORECASE)

    # Remove headers/footers
    text = re.sub(r'© \d{4}.*$', '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'Confidential.*$', '', text, flags=re.IGNORECASE | re.MULTILINE)

    # Fix spaces
    text = re.sub(r' +', ' ', text)

    # Fix newlines
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

    # Clean each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    return text.strip()


def clean_pdf_file(pdf_path, output_path):
    # Load PDF
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()

    # Clean all pages
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, doc in enumerate(docs, 1):
            cleaned = clean_text(doc.page_content)
            if cleaned:
                f.write(f"[Page {i}]\n{cleaned}\n\n")

    print(f"✅ Cleaned {len(docs)} pages from {Path(pdf_path).name}")
    return output_path


def clean_all_pdfs(input_dir, output_dir):
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    input_path.mkdir(parents=True, exist_ok=True)
    output_path.mkdir(parents=True, exist_ok=True)

    # Find all PDFs
    pdf_files = list(input_path.glob("*.pdf"))

    if not pdf_files:
        print(f"⚠️ No PDF files found in {input_dir}")
        print(f"   Please add PDF files to: {input_path.absolute()}")
        return []

    print(f"📄 Found {len(pdf_files)} PDF(s) to clean")
    print("-" * 40)

    # Clean each PDF
    cleaned_files = []
    for pdf_file in pdf_files:
        output_file = output_path / f"{pdf_file.stem}_cleaned.txt"
        clean_pdf_file(str(pdf_file), str(output_file))
        cleaned_files.append(str(output_file))

    print("-" * 40)
    print(f"✅ Cleaned {len(cleaned_files)} file(s) to {output_dir}")

    return cleaned_files
