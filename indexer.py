import os
import re
import glob

from graph import MemoryGraph

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
MEMORY_FILE = os.path.join(BASE_DIR, "MEMORY.md")
REFERENCE_DIR = os.path.join(BASE_DIR, "reference")
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
VECTOR_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")
COLLECTION_NAME = "memory_chunks"

def parse_markdown(file_path):
    """
    Parses a markdown file into chunks based on headers (## or #).
    Returns a list of dicts: {'content': text, 'metadata': {'source': filename, 'section': header}}
    """
    if not os.path.exists(file_path):
        return []
    
    source = os.path.relpath(file_path, BASE_DIR)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    chunks = []
    # Split by headers (## Header)
    sections = re.split(r'(^##?\s+.*$)', content, flags=re.MULTILINE)
    
    current_header = "Intro"
    current_content = sections[0].strip()
    if current_content:
        chunks.append({
            'content': current_content,
            'metadata': {'source': source, 'section': current_header}
        })

    for i in range(1, len(sections), 2):
        header = sections[i].strip().replace('#', '').strip()
        content = sections[i+1].strip() if i+1 < len(sections) else ""
        if content:
            chunks.append({
                'content': content,
                'metadata': {'source': source, 'section': header}
            })
            
    return chunks

def gather_all_files():
    """Collect all indexable markdown files."""
    files = []
    # MEMORY.md (primary)
    if os.path.exists(MEMORY_FILE):
        files.append(MEMORY_FILE)
    # reference/*.md (institutional knowledge)
    for f in sorted(glob.glob(os.path.join(REFERENCE_DIR, "*.md"))):
        files.append(f)
    # memory/*.md (daily logs)
    for f in sorted(glob.glob(os.path.join(MEMORY_DIR, "*.md"))):
        files.append(f)
    return files

def index_memory():
    print("🧠 Loading Sentence Transformer...")
    from sentence_transformers import SentenceTransformer
    import chromadb
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    print("📂 Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    
    print("📄 Parsing all knowledge files...")
    all_files = gather_all_files()
    chunks = []
    for f in all_files:
        file_chunks = parse_markdown(f)
        print(f"   📄 {os.path.relpath(f, BASE_DIR)}: {len(file_chunks)} chunks")
        chunks.extend(file_chunks)
    
    if not chunks:
        print("⚠️ No content found")
        return

    # --- GRAPH UPDATE ---
    print("🕸️  Updating Knowledge Graph...")
    graph = MemoryGraph()
    graph.build_from_chunks(chunks)
    # --------------------

    ids = [f"mem_{i}" for i in range(len(chunks))]
    documents = [c['content'] for c in chunks]
    metadatas = [c['metadata'] for c in chunks]
    
    print(f"🔢 Generating embeddings for {len(chunks)} chunks...")
    embeddings = model.encode(documents).tolist()
    
    print("💾 Storing in Vector DB (upsert)...")
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )
    # Clean up orphaned entries if chunk count decreased
    existing = collection.count()
    if existing > len(chunks):
        orphan_ids = [f"mem_{i}" for i in range(len(chunks), existing)]
        if orphan_ids:
            collection.delete(ids=orphan_ids)
            print(f"🧹 Cleaned {len(orphan_ids)} orphaned entries.")
    print("✅ Indexing Complete!")

if __name__ == "__main__":
    index_memory()
