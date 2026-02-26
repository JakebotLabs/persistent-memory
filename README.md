# Vector Memory Layer

This directory contains the persistent vector memory system for the agent.

## Components

- **`indexer.py`**: Reads `../MEMORY.md`, chunks it by header, embeds it using `all-MiniLM-L6-v2`, and stores it in a local ChromaDB.
- **`search.py`**: Command-line tool to semantically search the memory.
- **`chroma_db/`**: The persistent SQLite-based vector database (created after running indexer).
- **`venv/`**: Dedicated virtual environment to avoid dependency conflicts.

## Setup

1.  **Install Dependencies** (if not already done):
    ```bash
    python3 -m venv venv
    venv/bin/pip install -r ../requirements-memory.txt
    ```

2.  **Index Memory**:
    ```bash
    venv/bin/python indexer.py
    ```
    *Run this whenever `MEMORY.md` changes significantly.*

3.  **Search**:
    ```bash
    venv/bin/python search.py "your query here"
    ```

## Architecture

- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384d).
- **Storage**: ChromaDB (Local Persistent).
- **Chunking**: Markdown Header-based split.
