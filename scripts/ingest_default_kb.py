"""
Script to register and ingest the default AMD FAQ document.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal, init_db
from app.models.models import Document
from app.rag.pipeline import ingest_document, _is_openai_available

async def main():
    await init_db()
    
    faq_path = Path("data/knowledge_base/amd_faq.txt")
    if not faq_path.exists():
        print(f"[ERROR] FAQ file not found at: {faq_path.absolute()}")
        return

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        # Check if already registered
        result = await db.execute(select(Document).where(Document.filename == faq_path.name))
        doc = result.scalar_one_or_none()
        
        if not doc:
            doc = Document(filename=faq_path.name, status="indexing")
            db.add(doc)
            await db.commit()
            await db.refresh(doc)
            print(f"Registered document '{faq_path.name}' in database (id={doc.id})")
        else:
            print(f"Document '{faq_path.name}' is already registered (id={doc.id})")

        # Ingest document
        doc_id = doc.id
        
        if not _is_openai_available():
            print("[WARN] OpenAI API key is not configured or is a placeholder in .env.")
            print("[WARN] The document will be registered but actual embeddings cannot be generated yet.")
            print("[INFO] Fallback offline KeywordRetriever will be used during chat sessions.")
            doc.status = "ready"
            doc.chunk_count = 5 # Approximate chunk count for offline text
            await db.commit()
            print("Successfully registered FAQ document for offline fallback!")
            return

        print("OpenAI API key detected. Starting vector database ingestion...")
        try:
            # Run blocking ingestion in an executor thread
            loop = asyncio.get_event_loop()
            chunk_count = await loop.run_in_executor(
                None, 
                ingest_document, 
                faq_path, 
                doc_id
            )
            doc.status = "ready"
            doc.chunk_count = chunk_count
            await db.commit()
            print(f"Ingested successfully! Created {chunk_count} chunks in ChromaDB.")
        except Exception as e:
            print(f"[ERROR] Failed to ingest documents into ChromaDB: {e}")
            print("[INFO] Setting document status to 'error'. You can re-index via Admin Dashboard later.")
            doc.status = "error"
            await db.commit()

if __name__ == "__main__":
    asyncio.run(main())
