from typing import List, Dict

def chunk_text(text: str, chunk_size: int = 3000, overlap: int = 200) -> List[Dict]:
    chunks = []

    # Split by paragraphs first
    paragraphs = text.split('\n\n')

    current_chunk = ""
    current_start = 0

    for para in paragraphs:
        # If adding this paragraph exceeds chunk size
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            # Save current chunk
            chunks.append({
                'text': current_chunk.strip(),
                'chunk_id': len(chunks),
                'size': len(current_chunk)
            })

            # Keep overlap from end of current chunk
            overlap_text = current_chunk[-overlap:] if overlap > 0 else ""
            current_chunk = overlap_text + "\n\n" + para
        else:
            # Add paragraph to current chunk
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para

    # Add last chunk
    if current_chunk:
        chunks.append({
            'text': current_chunk.strip(),
            'chunk_id': len(chunks),
            'size': len(current_chunk)
        })

    return chunks