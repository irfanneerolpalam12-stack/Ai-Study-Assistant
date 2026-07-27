"""
AI Services Layer — Running 100% locally with Ollama.
RAG pipeline: FAISS + nomic-embed-text.
LLM: llama3.
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Environment Validation
# ─────────────────────────────────────────────────────────────────────────────

def _check_ai_config() -> str | None:
    """Return an error string if AI cannot be called, else None."""
    # Running 100% locally with Ollama, no API key required!
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Document Text Extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_text_from_file(file_path: str) -> str:
    """Extract plain text from PDF, DOCX, or TXT — with multiple fallbacks."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        return _extract_pdf(file_path)
    elif ext == '.docx':
        return _extract_docx(file_path)
    elif ext in ('.txt', '.md'):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.error(f'TXT read error: {e}')
            return ''
    else:
        logger.warning(f'Unsupported file type: {ext}')
        return ''


def _extract_pdf(file_path: str) -> str:
    """Try pdfplumber first, fall back to PyPDF2, then raw binary decode."""
    # Attempt 1: pdfplumber (best quality)
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        result = '\n\n'.join(text_parts).strip()
        if result:
            logger.info(f'PDF extracted via pdfplumber: {len(result)} chars')
            return result
    except Exception as e:
        logger.warning(f'pdfplumber failed ({e}), trying PyPDF2…')

    # Attempt 2: PyPDF2
    try:
        import PyPDF2
        text_parts = []
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        result = '\n\n'.join(text_parts).strip()
        if result:
            logger.info(f'PDF extracted via PyPDF2: {len(result)} chars')
            return result
    except ImportError:
        logger.warning('PyPDF2 not installed.')
    except Exception as e:
        logger.warning(f'PyPDF2 failed: {e}')

    logger.error(f'All PDF extraction methods failed for {file_path}')
    return ''


def _extract_docx(file_path: str) -> str:
    try:
        from docx import Document as DocxDocument
        doc = DocxDocument(file_path)
        return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        logger.error(f'DOCX extraction error: {e}')
        return ''


# ─────────────────────────────────────────────────────────────────────────────
# Text Chunking
# ─────────────────────────────────────────────────────────────────────────────

def _chunk_text(text: str, chunk_size: int = 400, overlap: int = 60) -> list[str]:
    """Split text into overlapping word-based chunks for better context coverage."""
    text = text.strip()
    if not text:
        return []
    words = text.split()
    if len(words) <= chunk_size:
        return [text]  # Small doc: one chunk
    chunks, i = [], 0
    while i < len(words):
        chunk = ' '.join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# RAG Pipeline — FAISS + sentence-transformers
# ─────────────────────────────────────────────────────────────────────────────

def ingest_document_to_chroma(document_id: int, text: str):
    """Chunk document text, embed via nomic-embed-text, and store in ChromaDB."""
    chunks = _chunk_text(text)
    if not chunks:
        print(f"⚠️  INGEST: No chunks generated for doc_{document_id} — text may be empty.")
        return

    print(f"\n🔄 INGEST: Starting ChromaDB ingestion for doc_{document_id} ({len(chunks)} chunks)…")

    try:
        import chromadb
        import ollama
        db_path = os.path.join(settings.BASE_DIR, 'chroma_db')
        client = chromadb.PersistentClient(path=db_path)
        collection_name = f"doc_{document_id}"

        # Delete old collection if it exists (re-ingestion)
        try:
            client.delete_collection(name=collection_name)
            print(f"🗑️  INGEST: Deleted old collection '{collection_name}'.")
        except Exception:
            pass

        collection = client.create_collection(name=collection_name)
        print(f"✅ INGEST: Created collection '{collection_name}'.")

        embeddings = []
        ids = []
        for i, chunk in enumerate(chunks):
            res = ollama.embeddings(model='nomic-embed-text', prompt=chunk)
            embeddings.append(res['embedding'])
            ids.append(f"chunk_{i}")
            if (i + 1) % 10 == 0:
                print(f"   … embedded {i + 1}/{len(chunks)} chunks")

        collection.add(
            embeddings=embeddings,
            documents=chunks,
            ids=ids
        )
        print(f"✅ INGEST: Successfully stored {len(chunks)} chunks in '{collection_name}'.")
        logger.info(f"Ingested {len(chunks)} chunks into ChromaDB collection {collection_name}")
    except Exception as e:
        print(f"❌ INGEST: ChromaDB ingestion error for doc_{document_id} — {e}")
        logger.error(f'ChromaDB ingestion error: {e}', exc_info=True)



# ─────────────────────────────────────────────────────────────────────────────
# LLM Provider
# ─────────────────────────────────────────────────────────────────────────────

def _chat_completion(messages: list[dict], temperature: float = 0.7) -> str:
    """Dispatch to the configured LLM provider (Ollama)."""
    return _ollama_chat(messages, temperature)


def _ollama_chat(messages: list[dict], temperature: float) -> str:
    try:
        import ollama
        response = ollama.chat(
            model='llama3',
            messages=messages,
            options={'temperature': temperature}
        )
        return response['message']['content'].strip()
    except Exception as e:
        logger.error(f'Ollama error: {e}')
        raise RuntimeError(f'Ollama request failed: {e}') from e


# ─────────────────────────────────────────────────────────────────────────────
# High-Level AI Actions
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_STUDY_ASSISTANT = (
    'You are an expert AI study assistant. You are concise, accurate, and helpful. '
    'Use Markdown formatting in your responses where appropriate.'
)


def generate_rag_response(chat_id, user_message, active_document, history=None):
    """
    RAG-aware chat function.
    1. If a document is attached, retrieve top-5 relevant chunks from ChromaDB.
    2. Fall back to raw extracted_text keyword search if ChromaDB isn't ready yet.
    3. Inject context into a STRICT system prompt so llama3 NEVER says 'share the PDF'.
    """
    import ollama
    import chromadb

    if history is None:
        history = []

    context_text = ""

    # ── Step 1: Retrieve context ───────────────────────────────────────────────
    if active_document:
        doc_id = active_document.id
        print(f"\n📄 RAG: Active document = doc_{doc_id} ('{active_document.title}')")

        chroma_success = False

        # ── Try ChromaDB first ─────────────────────────────────────────────
        try:
            db_path = os.path.join(settings.BASE_DIR, 'chroma_db')
            client = chromadb.PersistentClient(path=db_path)
            collection_name = f"doc_{doc_id}"

            existing = [c.name for c in client.list_collections()]
            print(f"🗄️  RAG: ChromaDB collections available: {existing}")

            if collection_name not in existing:
                print(f"⚠️  RAG: Collection '{collection_name}' not found — ingestion may still be running.")
            else:
                chroma_collection = client.get_collection(name=collection_name)
                n_stored = chroma_collection.count()
                print(f"✅ RAG: Collection '{collection_name}' has {n_stored} chunks.")

                # Embed the user question
                query_embedding = ollama.embeddings(
                    model='nomic-embed-text',
                    prompt=user_message
                )['embedding']
                print(f"✅ RAG: Query embedded ({len(query_embedding)}-dim).")

                n_results = min(5, n_stored)
                results = chroma_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                )

                docs = results.get('documents', [[]])[0]
                print(f"✅ RAG: ChromaDB returned {len(docs)} chunks.")

                if docs:
                    context_text = "\n\n...\n\n".join(docs)
                    chroma_success = True
                else:
                    print("⚠️  RAG: ChromaDB returned 0 docs for this query.")

        except Exception as e:
            print(f"❌ RAG: ChromaDB error — {e}")
            logger.error(f"ChromaDB retrieval error: {e}", exc_info=True)

        # ── Fallback: keyword search on raw extracted_text ─────────────────
        if not chroma_success:
            raw_text = getattr(active_document, 'extracted_text', '') or ''
            if raw_text:
                print(f"🔄 RAG: Falling back to keyword search on {len(raw_text)} chars of extracted text.")
                chunks = _chunk_text(raw_text)
                keywords = set(re.sub(r'[^\w\s]', '', user_message.lower()).split())
                scored = []
                for chunk in chunks:
                    chunk_words = set(re.sub(r'[^\w\s]', '', chunk.lower()).split())
                    scored.append((len(keywords & chunk_words), chunk))
                scored.sort(key=lambda x: x[0], reverse=True)
                best = [c for _, c in scored[:5] if c]
                if not best:
                    best = chunks[:5]
                context_text = "\n\n...\n\n".join(best)
                print(f"✅ RAG: Keyword fallback selected {len(best)} chunks.")
            else:
                print("⚠️  RAG: No extracted text yet — answering without document context.")
    else:
        print("ℹ️  RAG: No active document — general chat mode.")

    # ── Step 2: Build strict system prompt ────────────────────────────────────
    if context_text.strip():
        system_prompt = (
            "You are an expert study assistant. "
            "You MUST answer the user's question using ONLY the provided document context below. "
            "Do NOT ask the user to share or provide any document — it has already been provided to you here. "
            "If the specific answer cannot be found in the context, say exactly: "
            "'This information is not found in the provided document.' "
            "Do NOT make up or infer information not present in the context.\n\n"
            f"--- START DOCUMENT CONTEXT ---\n{context_text}\n--- END DOCUMENT CONTEXT ---"
        )
        print(f"📝 RAG: Prompt built WITH context ({len(context_text)} chars).")
    else:
        system_prompt = (
            "You are a helpful AI study assistant. "
            "Answer general study questions to the best of your ability."
        )
        print("📝 RAG: Prompt built WITHOUT context (general mode).")

    # ── Step 3: Call llama3 ───────────────────────────────────────────────────
    messages = [{'role': 'system', 'content': system_prompt}]
    messages.extend(history)
    messages.append({'role': 'user', 'content': user_message})

    print(f"🚀 RAG: Sending {len(messages)} message(s) to llama3…")

    try:
        response = ollama.chat(model='llama3', messages=messages)
        reply = response['message']['content']
        print(f"✅ RAG: llama3 responded ({len(reply)} chars).")
        return reply
    except Exception as e:
        logger.error(f"Ollama chat error: {e}", exc_info=True)
        raise RuntimeError(f"Ollama request failed: {e}") from e



def summarize_document(text: str) -> dict:
    """Return structured summary: key_points (list) + executive_summary (str)."""
    if len(text) > 12000:
        text = text[:12000] + '\n\n[...document truncated for summary...]'

    prompt = (
        'Summarize the following study document. Return a valid JSON object with exactly two keys:\n'
        '1. "key_points": a list of 5-8 concise bullet-point strings\n'
        '2. "executive_summary": a 3-4 sentence paragraph summary\n\n'
        f'Document:\n{text}'
    )
    raw = _chat_completion([
        {'role': 'system', 'content': SYSTEM_STUDY_ASSISTANT},
        {'role': 'user', 'content': prompt},
    ], temperature=0.3)

    raw = raw.strip().lstrip('```json').lstrip('```').rstrip('```').strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {'key_points': [raw], 'executive_summary': raw}


def generate_quiz(text: str, num_questions: int = 10) -> list[dict]:
    """Generate MCQ questions from study material."""
    if len(text) > 10000:
        text = text[:10000]

    prompt = (
        f'Generate exactly {num_questions} multiple-choice quiz questions from the text below. '
        'Return a valid JSON array where each element has these keys:\n'
        '- "question": the question string\n'
        '- "options": a list of exactly 4 answer strings (A, B, C, D)\n'
        '- "answer": the correct option string (must match one of the options exactly)\n'
        '- "explanation": a brief explanation of the correct answer\n\n'
        f'Study Material:\n{text}'
    )
    raw = _chat_completion([
        {'role': 'system', 'content': SYSTEM_STUDY_ASSISTANT},
        {'role': 'user', 'content': prompt},
    ], temperature=0.5)

    raw = raw.strip().lstrip('```json').lstrip('```').rstrip('```').strip()
    try:
        questions = json.loads(raw)
        return questions if isinstance(questions, list) else []
    except json.JSONDecodeError:
        logger.error('Quiz JSON parse error')
        return []


def generate_flashcards(text: str, deck_title: str = 'Study Deck') -> list[dict]:
    """Generate front/back flashcards from study material."""
    if len(text) > 8000:
        text = text[:8000]

    prompt = (
        'Generate 10-15 study flashcards from the text below. '
        'Return a valid JSON array where each element has:\n'
        '- "front": a question or term (1 sentence)\n'
        '- "back": the answer or definition (1-3 sentences)\n\n'
        f'Study Material:\n{text}'
    )
    raw = _chat_completion([
        {'role': 'system', 'content': SYSTEM_STUDY_ASSISTANT},
        {'role': 'user', 'content': prompt},
    ], temperature=0.5)

    raw = raw.strip().lstrip('```json').lstrip('```').rstrip('```').strip()
    try:
        cards = json.loads(raw)
        return cards if isinstance(cards, list) else []
    except json.JSONDecodeError:
        logger.error('Flashcard JSON parse error')
        return []


def improve_notes(raw_notes: str) -> str:
    """Reformat raw notes into a clean Markdown study guide."""
    prompt = (
        'Rewrite the following raw study notes into a clean, well-structured Markdown study guide. '
        'Use headings, bullet points, bold for key terms, and code blocks where relevant. '
        'Preserve all the original information — only improve formatting and clarity.\n\n'
        f'Raw Notes:\n{raw_notes}'
    )
    return _chat_completion([
        {'role': 'system', 'content': SYSTEM_STUDY_ASSISTANT},
        {'role': 'user', 'content': prompt},
    ], temperature=0.4)


def generate_study_plan(topics: list[str], exam_date: str, hours_per_day: float = 2.0) -> dict:
    """Generate a structured daily study plan."""
    topics_str = ', '.join(topics) if topics else 'General study topics'
    prompt = (
        f'Create a structured daily study plan for the following topics: {topics_str}.\n'
        f'Exam date: {exam_date}\n'
        f'Available study hours per day: {hours_per_day}\n\n'
        'Return a valid JSON object with:\n'
        '- "total_days": number of days until the exam\n'
        '- "daily_plan": a list of objects, each with "day" (number), "date" (YYYY-MM-DD), '
        '"topic" (string), "tasks" (list of strings), "duration_hours" (float)\n'
        '- "tips": a list of 3-5 general study tip strings'
    )
    raw = _chat_completion([
        {'role': 'system', 'content': SYSTEM_STUDY_ASSISTANT},
        {'role': 'user', 'content': prompt},
    ], temperature=0.4)

    raw = raw.strip().lstrip('```json').lstrip('```').rstrip('```').strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {'error': 'Could not generate study plan. Please try again.', 'raw': raw}
