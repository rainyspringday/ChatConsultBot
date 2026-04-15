from typing import List, Dict


class TextChunkerService:
    def __init__(self, chunk_size: int = 1000, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str) -> List[Dict]:
        chunks = []
        paragraphs = text.split('\n\n')

        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) > self.chunk_size and current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "chunk_id": len(chunks),
                    "size": len(current_chunk)
                })

                overlap_text = current_chunk[-self.overlap:] if self.overlap > 0 else ""
                current_chunk = overlap_text + "\n\n" + para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "chunk_id": len(chunks),
                "size": len(current_chunk)
            })

        return chunks