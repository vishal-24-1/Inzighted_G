# 🏗️ Celery Architecture Diagram

## System Architecture Overview

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                         CLIENT LAYER                            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                 │
                                 │ POST /api/ingest/
                                 │ (file upload)
                                 ↓
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                       DJANGO APPLICATION                        ┃
┃                                                                 ┃
┃  ┌─────────────────────────────────────────────────────────┐   ┃
┃  │  IngestView (api/views.py)                             │   ┃
┃  │                                                         │   ┃
┃  │  1. Receive file upload                                │   ┃
┃  │  2. Save to temp storage                               │   ┃
┃  │  3. Upload to S3                                       │   ┃
┃  │  4. Create Document record (status='processing')       │   ┃
┃  │  5. Enqueue Celery task                                │   ┃
┃  │     process_document.delay(s3_key, user_id, doc_id)   │   ┃
┃  │  6. Return immediate response (202 Accepted)           │   ┃
┃  └─────────────────────────────────────────────────────────┘   ┃
┃                                 │                               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                 │
                                 │ Task enqueued
                                 ↓
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                      REDIS MESSAGE BROKER                       ┃
┃                                                                 ┃
┃  ┌─────────────────────────────────────────────────────────┐   ┃
┃  │  Task Queue (DB 0)                                      │   ┃
┃  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │   ┃
┃  │  │ Task 1  │  │ Task 2  │  │ Task 3  │  │ Task 4  │  │   ┃
┃  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │   ┃
┃  └─────────────────────────────────────────────────────────┘   ┃
┃                                                                 ┃
┃  ┌─────────────────────────────────────────────────────────┐   ┃
┃  │  Result Backend (DB 1)                                  │   ┃
┃  │  - Task status                                          │   ┃
┃  │  - Task results                                         │   ┃
┃  │  - Error information                                    │   ┃
┃  └─────────────────────────────────────────────────────────┘   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ↓                         ↓
    ┏━━━━━━━━━━━━━━━━━━━━┓      ┏━━━━━━━━━━━━━━━━━━━━┓
    ┃   CELERY WORKER 1  ┃      ┃   CELERY WORKER 2  ┃
    ┃   (Concurrency: 4) ┃      ┃   (Concurrency: 4) ┃
    ┗━━━━━━━━━━━━━━━━━━━━┛      ┗━━━━━━━━━━━━━━━━━━━━┛
                    ↓                         ↓
    ┏━━━━━━━━━━━━━━━━━━━━┓      ┏━━━━━━━━━━━━━━━━━━━━┓
    ┃   CELERY WORKER 3  ┃      ┃   CELERY WORKER 4  ┃
    ┃   (Concurrency: 4) ┃      ┃   (Concurrency: 4) ┃
    ┗━━━━━━━━━━━━━━━━━━━━┛      ┗━━━━━━━━━━━━━━━━━━━━┛
                    │
                    │ All workers execute
                    ↓
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                   DOCUMENT PROCESSING PIPELINE                  ┃
┃                     (api/tasks.py)                              ┃
┃                                                                 ┃
┃  ┌─────────────────────────────────────────────────────────┐   ┃
┃  │  process_document(s3_key, user_id, document_id)        │   ┃
┃  │                                                         │   ┃
┃  │  Step 1: Download from S3                              │   ┃
┃  │           ↓                                            │   ┃
┃  │  Step 2: Extract text (PDF/DOCX + OCR fallback)       │   ┃
┃  │           ↓                                            │   ┃
┃  │  Step 3: Chunk text (token-aware, spaCy)              │   ┃
┃  │           ↓                                            │   ┃
┃  │  Step 4: Generate embeddings (Gemini Embedding-001)   │   ┃
┃  │           ↓                                            │   ┃
┃  │  Step 5: Upload to Pinecone (with tenant isolation)   │   ┃
┃  │           ↓                                            │   ┃
┃  │  Step 6: Update Document status = 'completed'         │   ┃
┃  └─────────────────────────────────────────────────────────┘   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                    │              │              │
                    ↓              ↓              ↓
            ┌──────────────┬──────────────┬──────────────┐
            │              │              │              │
            ↓              ↓              ↓              ↓
    ┏━━━━━━━━━━┓   ┏━━━━━━━━━┓   ┏━━━━━━━━━━━┓   ┏━━━━━━━━━━┓
    ┃ AWS S3   ┃   ┃ Gemini  ┃   ┃ Pinecone   ┃   ┃ Database ┃
    ┃ Storage  ┃   ┃ AI API  ┃   ┃ Vector DB  ┃   ┃ PostgreSQL┃
    ┗━━━━━━━━━━┛   ┗━━━━━━━━━┛   ┗━━━━━━━━━━━┛   ┗━━━━━━━━━━┛
```

---

## Task Flow Sequence

```
┌─────────────┐
│   Upload    │
│  Document   │
└──────┬──────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  Django receives request                │
│  - Authenticates user                   │
│  - Validates file                       │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  Save to temp & upload to S3            │
│  - Generate S3 key                      │
│  - Upload file                          │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  Create Document record                 │
│  - status = 'processing'                │
│  - s3_key stored                        │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  Enqueue Celery task                    │
│  process_document.delay(...)            │
└──────┬──────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────┐
│  Return 202 Accepted immediately        │
│  {                                      │
│    "message": "Processing started",    │
│    "task_id": "...",                   │
│    "async": true                       │
│  }                                      │
└──────┬──────────────────────────────────┘
       │
       │ (User is free, processing continues in background)
       │
       ↓
┌─────────────────────────────────────────┐
│  Celery worker picks up task           │
│  - Downloads from S3                    │
│  - Extracts text                        │
│  - Chunks content                       │
│  - Generates embeddings                 │
│  - Uploads to Pinecone                  │
└──────┬──────────────────────────────────┘
       │
       ├──── Success ────┐
       │                  │
       ↓                  ↓
┌──────────────┐   ┌──────────────┐
│Update status │   │ Update status│
│'completed'   │   │   'failed'   │
└──────────────┘   └──────────────┘
```

---

## Retry Flow

```
┌─────────────────┐
│  Task Execution │
└────────┬────────┘
         │
         ↓
    ┌─────────┐
    │ Success?│
    └────┬────┘
         │
    ┌────┴────┐
    │   NO    │    YES
    ↓         └────────────────────┐
┌─────────┐                        │
│ Retry   │                        │
│ Count?  │                        │
└────┬────┘                        │
     │                             │
     ├── < 3 retries               │
     │                             │
     ↓                             │
┌──────────────┐                   │
│ Wait with    │                   │
│ backoff:     │                   │
│ - 1st: 2s    │                   │
│ - 2nd: 4s    │                   │
│ - 3rd: 8s    │                   │
└──────┬───────┘                   │
       │                           │
       ↓                           │
┌──────────────┐                   │
│ Retry task   │                   │
└──────┬───────┘                   │
       │                           │
       └───────┐                   │
               │                   │
     ≥ 3 retries                  │
               │                   │
               ↓                   ↓
        ┌────────────┐      ┌───────────┐
        │Mark 'failed'│      │Mark 'done'│
        │Log to Sentry│      │           │
        └─────────────┘      └───────────┘
```

---

## Component Communication

```
┌──────────────────────────────────────────────────────────┐
│                    Django Application                    │
│                                                          │
│  ┌─────────┐    ┌─────────┐    ┌──────────────────┐   │
│  │ Views   │───→│ Tasks   │───→│ Task Enqueuing   │   │
│  └─────────┘    └─────────┘    └──────────────────┘   │
└───────────────────────────┬──────────────────────────────┘
                            │
                            ↓
                    ┌──────────────┐
                    │  Redis Broker│
                    └──────┬───────┘
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ↓             ↓             ↓
      ┌──────────┐  ┌──────────┐  ┌──────────┐
      │Worker 1  │  │Worker 2  │  │Worker 3/4│
      └────┬─────┘  └────┬─────┘  └────┬─────┘
           │             │             │
           └─────────────┼─────────────┘
                         │
            ┌────────────┼────────────┐
            │            │            │
            ↓            ↓            ↓
      ┌─────────┐  ┌─────────┐  ┌─────────┐
      │   S3    │  │ Gemini  │  │Pinecone │
      └─────────┘  └─────────┘  └─────────┘
```

---

## Data Flow

```
User Document (PDF/DOCX)
    │
    ↓
┌──────────────────┐
│ Upload to Django │
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│  Save to S3      │  ← Document storage
└────────┬─────────┘
         │
         ↓
┌──────────────────────────────────┐
│  Celery Task Processing:         │
│                                  │
│  1. Binary File (from S3)        │
│     ↓                            │
│  2. Extracted Text               │
│     ↓                            │
│  3. Text Chunks                  │
│     ["chunk 1", "chunk 2", ...]  │
│     ↓                            │
│  4. Embeddings                   │
│     [[0.1, 0.2, ...], ...]       │
│     ↓                            │
│  5. Pinecone Vectors             │
│     {id, values, metadata}       │
└──────────────────────────────────┘
         │
         ↓
┌──────────────────┐
│ Store in Pinecone│  ← Vector database
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│ Update Document  │  ← Status tracking
│ status='completed'│
└──────────────────┘
```

---

## Monitoring & Observability

```
                    ┌─────────────────┐
                    │ Celery Workers  │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ↓                   ↓                   ↓
    ┌─────────┐        ┌─────────┐        ┌─────────┐
    │ Console │        │ Sentry  │        │ Flower  │
    │  Logs   │        │ Errors  │        │Dashboard│
    └─────────┘        └─────────┘        └─────────┘
         │                   │                   │
         └───────────────────┴───────────────────┘
                             │
                             ↓
                    ┌─────────────────┐
                    │   Monitoring    │
                    │   Dashboard     │
                    └─────────────────┘
```

---

## Worker Lifecycle

```
Start Workers
    │
    ↓
┌──────────────────────┐
│ Initialize Celery    │
│ - Connect to Redis   │
│ - Load configuration │
└──────────┬───────────┘
           │
           ↓
┌──────────────────────┐
│ Register Tasks       │
│ - process_document   │
│ - test_celery        │
└──────────┬───────────┘
           │
           ↓
┌──────────────────────┐
│ Poll for Tasks       │ ←──┐
└──────────┬───────────┘    │
           │                │
           ↓                │
    ┌──────────┐            │
    │Task found?            │
    └────┬─────┘            │
         │                  │
    YES  │  NO ─────────────┘
         │                  
         ↓                  
┌──────────────────────┐
│ Execute Task         │
│ - Run processing     │
│ - Handle errors      │
│ - Update status      │
└──────────┬───────────┘
           │
           ↓
┌──────────────────────┐
│ Report Result        │
│ - Store in Redis     │
│ - Log completion     │
└──────────┬───────────┘
           │
           └──────────────────┐
                              │
           ┌──────────────────┘
           │
           ↓
    ┌──────────────┐
    │ Max tasks    │
    │ reached?     │
    └──────┬───────┘
           │
      YES  │  NO
           │   └────────────┐
           ↓                │
    ┌──────────┐            │
    │ Restart  │            │
    │ Worker   │            │
    └──────────┘            │
           │                │
           └────────────────┘
                │
                ↓
         Continue polling
```

This architecture provides a robust, scalable system for asynchronous document processing with proper error handling, monitoring, and recovery mechanisms.
