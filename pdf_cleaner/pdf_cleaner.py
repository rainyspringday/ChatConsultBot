import re
import unicodedata
from pathlib import Path
from collections import Counter

from langchain_community.document_loaders import PyPDFLoader
from src.core.config import Config



def clean_text(text):
    # --- Normalize unicode ---
    text = unicodedata.normalize("NFKC", text)

    # --- Remove control characters ---
    text = re.sub(r"[\x00-\x1f\x7f]", "", text)

    # --- Fix hyphenated line breaks ---
    text = re.sub(r"(\w+)-\s*\n(\w+)", r"\1\2", text)

    # --- Remove URLs & emails ---
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"\S+@\S+\.\S+", "", text)

    # --- Remove licensing / copyright / disclaimers ---
    license_patterns = [
        r"copyright © \d{4}.*",
        r"creative commons.*",
        r"all rights reserved.*",
        r"licensed under.*",
        r"this material is provided.*",
        r"no part of this.*",
        r"permission to reproduce.*",
    ]
    for pat in license_patterns:
        text = re.sub(pat, "", text, flags=re.I)

    # --- Remove page numbers ---
    text = re.sub(r"Page \d+(\s+of\s+\d+)?", "", text, flags=re.I)
    text = re.sub(r"\n\s*\d+\s*\n", "\n", text)

    # --- Normalize bullet points ---
    text = re.sub(r"[•·●◦]", "-", text)

    # --- Remove repeated headers/footers (business docs often repeat titles) ---
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    freq = Counter(lines)
    threshold = max(3, len(lines) * 0.10)  # appears on >10% of pages
    lines = [l for l in lines if freq[l] < threshold]

    # --- Rebuild paragraphs (simple, safe) ---
    rebuilt = []
    buffer = ""

    for line in lines:
        if not line:
            if buffer:
                rebuilt.append(buffer.strip())
                buffer = ""
            continue

        # If line ends with punctuation, treat as paragraph end
        if re.search(r"[.!?]$", line):
            buffer += " " + line
            rebuilt.append(buffer.strip())
            buffer = ""
        else:
            buffer += " " + line

    if buffer:
        rebuilt.append(buffer.strip())

    # --- Final cleanup ---
    text = "\n\n".join(rebuilt)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

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


def clean_all_pdfs():
    project_root = Config.root
    input_path = project_root / Path(Config.input_dir)
    output_path = project_root / Path(Config.output_dir)

    input_path.mkdir(parents=True, exist_ok=True)
    output_path.mkdir(parents=True, exist_ok=True)

    # Find all PDFs
    pdf_files = list(input_path.glob("*.pdf"))

    if not pdf_files:
        print(f"⚠️ No PDF files found")
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
    print(f"✅ Cleaned {len(cleaned_files)} file(s)")

    return cleaned_files

if __name__ == "__main__":
    clean_all_pdfs()