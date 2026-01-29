# ADK RAG Sample Code

A RAG (Retrieval-Augmented Generation) agent using Google ADK and Vertex AI Search.

## Overview

This project demonstrates two approaches to building a RAG agent:

| Approach | File | Description |
|----------|------|-------------|
| **Custom Tool** | `agent_with_custom_search_tool.py` | Manual Discovery Engine API calls, full control over search logic |
| **Built-in Tool** | `agent_with_built_in_search_tool.py` | Uses `VertexAiSearchTool`, automatic grounding, less code |

## Architecture

```
PDF Document
    ↓
[00_preprocess.py] PDF → HTML
    ↓
[01_prepare_data.py] Generate metadata.jsonl
    ↓
[02_upload_to_gcs.py] Upload to GCS
    ↓
[03_create_datastore.py] Create Vertex AI Search datastore
    ↓
[04_import_documents.py] Import & index documents
    ↓
Vertex AI Search (chunking + embeddings)
    ↓
Agent queries → Grounded responses
```

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/viorelspinu/adk_rag_sample_code.git
cd adk_rag_sample_code
uv sync
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
PROJECT_ID=your-gcp-project-id
LOCATION=global
REGION=us-central1
DATASTORE_ID=your-datastore-id
BUCKET_NAME=your-gcs-bucket
SITE_PREFIX=rag-documents
MODEL=gemini-2.0-flash
GOOGLE_APPLICATION_CREDENTIALS=your-service-account.json
```

### 3. Place credentials

Put your GCP service account JSON file in the project root.

## Data Ingestion

Run these scripts in order to ingest a PDF into Vertex AI Search:

```bash
# 1. Convert PDF to HTML
uv run python ingestion/00_preprocess.py --input your-doc.pdf --output output/doc.html

# 2. Prepare metadata
uv run python ingestion/01_prepare_data.py --input output/doc.html

# 3. Upload to GCS
uv run python ingestion/02_upload_to_gcs.py

# 4. Create datastore (only once)
uv run python ingestion/03_create_datastore.py

# 5. Import documents
uv run python ingestion/04_import_documents.py
```

Wait 30 min - 2 hours for indexing to complete. Check status in [GCP Console](https://console.cloud.google.com/gen-app-builder/data-stores).

## Running the Agent

### Custom Search Tool

```bash
# Interactive mode
uv run python src/agent_with_custom_search_tool.py

# Single question
uv run python src/agent_with_custom_search_tool.py -q "What is X?"
```

### Built-in Search Tool

```bash
# Interactive mode
uv run python src/agent_with_built_in_search_tool.py

# Single question
uv run python src/agent_with_built_in_search_tool.py -q "What is X?"
```

## Project Structure

```
├── .env.example          # Environment template
├── pyproject.toml        # Dependencies
├── src/
│   ├── config.py         # Configuration (loads from .env)
│   ├── prompts.py        # Agent system prompts
│   ├── search_tool.py    # Custom Vertex AI Search tool
│   ├── agent_with_custom_search_tool.py
│   └── agent_with_built_in_search_tool.py
└── ingestion/
    ├── 00_preprocess.py      # PDF → HTML
    ├── 01_prepare_data.py    # Generate metadata
    ├── 02_upload_to_gcs.py   # Upload to GCS
    ├── 03_create_datastore.py # Create datastore
    └── 04_import_documents.py # Import documents
```

## Requirements

- Python 3.11+
- GCP project with Vertex AI Search enabled
- Service account with permissions:
  - `discoveryengine.admin`
  - `storage.admin`

## Resources

- [ADK Vertex AI Search Tool](https://google.github.io/adk-docs/tools/google-cloud/vertex-ai-search/)
- [Vertex AI Search Grounding](https://google.github.io/adk-docs/grounding/vertex_ai_search_grounding/)
- [Vertex AI Agent Builder](https://console.cloud.google.com/gen-app-builder)
