# Documents And RAG

The Documents capability stores user-uploaded files, chunks them, indexes them in the vector store, and makes them searchable through the `search_local_files` tool.

## Supported Upload Types

The Documents API supports:

- `.pdf`
- `.docx`
- `.txt`
- `.md`
- `.html`

Maximum document upload size is 50 MB.

Chat attachments are a separate feature and have a 10 MB limit. Chat attachments are sent as immediate context; Documents uploads are persisted and indexed for later retrieval.

## Step-By-Step Use

1. Sign in.
2. Open Documents.
3. Upload a supported file.
4. Wait for the upload to complete.
5. The backend creates a database record with `is_indexed=false`.
6. The backend starts asynchronous indexing.
7. Refresh or reopen Documents to confirm `is_indexed=true`.
8. Open Tools and enable `search_local_files` if it is not already enabled.
9. Ask Chat a question about the uploaded document.
10. The agent calls `search_local_files`, retrieves relevant chunks, and answers from them.

## Storage Flow

Endpoint:

```text
POST /api/documents/upload
```

Backend flow:

1. Validate extension.
2. Read file bytes.
3. Enforce 50 MB size limit.
4. Hash content with SHA-256.
5. Reject duplicate content for the same user.
6. Save file under `user_documents/{user_id}/`.
7. Create a `UserDocument` row.
8. Start `index_user_document()` in a background task.

Stored filenames are generated as:

```text
{first_16_chars_of_hash}_{sanitized_original_filename}
```

## Indexing Flow

`index_user_document()`:

1. Opens a fresh database session for the background task.
2. Reads the user's preferred `embedding_model`.
3. Loads the file with LangChain loaders:
   - `PyPDFLoader` for PDF.
   - `Docx2txtLoader` for DOCX.
   - `TextLoader` for TXT and Markdown.
   - `UnstructuredHTMLLoader` for HTML if available.
   - BeautifulSoup fallback for HTML.
4. Splits content with `RecursiveCharacterTextSplitter`.
5. Uses `CHUNK_SIZE` and `CHUNK_OVERLAP` from settings.
6. Writes chunks to collection `user_documents_{user_id}`.
7. Marks the document indexed in SQLite.

Chunk metadata includes:

- `document_id`
- `user_id`
- `file_name`
- `file_path`
- `file_type`
- `chunk_index`
- `total_chunks`

## Retrieval Flow

The `search_local_files` tool:

1. Receives the user query.
2. Looks up the user's preferred embedding model.
3. Searches `user_documents_{user_id}`.
4. Returns the top matching chunks as source/content blocks.
5. Does not fall back to global `./data` documents when user context exists and no user documents match.

## Document API

- `POST /api/documents/upload` uploads and asynchronously indexes a document.
- `GET /api/documents/` lists the current user's documents.
- `DELETE /api/documents/{document_id}` deletes a document record and file.
- `POST /api/documents/{document_id}/index` reindexes an existing document.

## Vector Stores

Chroma is the default.

```env
VECTOR_STORE=chroma
CHROMA_PATH=./chroma_db
```

Qdrant is optional.

```env
VECTOR_STORE=qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=agent_memory
```

Docker can start Qdrant with:

```powershell
docker compose --profile qdrant up
```

## Embedding Settings

Relevant environment variables:

```env
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
EMBEDDING_DIMENSION=1024
EMBEDDING_DEVICE=auto
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_RETRIEVAL_RESULTS=10
```

Users can also select an embedding model in Settings; document indexing and retrieval attempt to use the user's configured model.

## Known Limitations

- Document deletion removes the stored file and database record, but vector chunk deletion is marked TODO in `backend/api/documents.py`. Reindexing or clearing collections may be needed if deleted chunks still appear.
- Changing embedding models can produce dimensionality mismatches in persisted vector collections. Chroma has recovery logic for known collections, but user document collections may still need reindexing.
- Background indexing errors are logged but do not block the upload response.
