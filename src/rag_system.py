import subprocess
from pathlib import Path
from typing import List, Dict, Optional


class SimpleRAG:
    """Simple RAG system using Ollama LLM"""

    def __init__(self, cleaned_texts_folder: str = "data/cleaned_files", model: str = "llama2"):
        self.model = model
        self.chunks = []
        self._load_texts(cleaned_texts_folder)

    def _load_texts(self, folder: str):
        """Load and chunk cleaned text files"""
        folder_path = Path(folder)

        if not folder_path.exists():
            print(f"⚠️ Folder not found: {folder}")
            return

        for file_path in folder_path.glob("*.txt"):
            text = file_path.read_text(encoding='utf-8')

            # Split into chunks by paragraphs
            paragraphs = text.split('\n\n')

            for para in paragraphs:
                if len(para.strip()) > 50:
                    self.chunks.append({
                        'text': para.strip(),
                        'file': file_path.name
                    })

        print(f"✅ Loaded {len(self.chunks)} chunks from {folder}")

    def _find_relevant_chunks(self, question: str, top_k: int = 3) -> List[Dict]:
        """Find relevant chunks using keyword matching"""
        question_words = set(question.lower().split())

        if not question_words:
            return []

        # Score each chunk
        scored_chunks = []
        for chunk in self.chunks:
            chunk_words = set(chunk['text'].lower().split())
            common = question_words.intersection(chunk_words)
            score = len(common) / len(question_words)
            scored_chunks.append((chunk, score))

        # Sort and get top k
        scored_chunks.sort(key=lambda x: x[1], reverse=True)

        relevant = []
        for chunk, score in scored_chunks[:top_k]:
            if score > 0:
                relevant.append({
                    'text': chunk['text'],
                    'file': chunk['file'],
                    'score': score
                })

        return relevant

    def _ask_ollama(self, prompt: str, timeout: int = 60) -> Optional[str]:
        """Send prompt to local Ollama"""
        try:
            result = subprocess.run(
                ['ollama', 'run', self.model, prompt],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            print("⚠️ Ollama timeout - response took too long")
            return None
        except FileNotFoundError:
            print("⚠️ Ollama not found. Please install Ollama from: https://ollama.ai")
            print("   Then run: ollama pull llama2")
            return None
        except Exception as e:
            print(f"⚠️ Error: {e}")
            return None

    def ask(self, question: str, verbose: bool = True) -> str:
        if verbose:
            print(f"\n🔍 Searching for: {question}")

        # Find relevant chunks
        relevant = self._find_relevant_chunks(question)

        if not relevant:
            return "❌ No relevant information found in documents."

        if verbose:
            print(f"📚 Found {len(relevant)} relevant chunks")
            for r in relevant:
                print(f"   - {r['file']} (relevance: {r['score']:.0%})")

        # Create context from relevant chunks
        context = "\n\n".join([r['text'] for r in relevant])

        # Create prompt for Ollama
        prompt = f"""You are a helpful assistant. Answer the question based ONLY on the context below.

CONTEXT:
{context}

QUESTION: {question}

ANSWER (be concise and based only on the context):"""

        if verbose:
            print("🤖 Asking Ollama for answer...")

        # Get answer from Ollama
        answer = self._ask_ollama(prompt)

        if answer:
            # Add sources to answer
            sources = "\n".join([f"  • {r['file']}" for r in relevant])
            return f"\n📝 ANSWER:\n{answer}\n\n📚 SOURCES:\n{sources}"
        else:
            # Fallback: return most relevant chunk without LLM
            return f"\n📝 ANSWER (from document):\n{relevant[0]['text']}\n\n📚 SOURCE:\n{relevant[0]['file']}"

    def ask_simple(self, question: str) -> str:
        """Simpler version - just returns answer without extra formatting"""
        relevant = self._find_relevant_chunks(question, top_k=2)

        if not relevant:
            return "No relevant information found."

        context = "\n\n".join([r['text'] for r in relevant])
        prompt = f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"

        answer = self._ask_ollama(prompt)
        return answer if answer else relevant[0]['text']
