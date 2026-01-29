#!/usr/bin/env python3
"""
Create Vertex AI Search datastore with chunking enabled.

Usage:
    uv run python ingestion/03_create_datastore.py
    uv run python ingestion/03_create_datastore.py --chunk-size 500
"""

import argparse
import sys
import os
from pathlib import Path
from google.cloud import discoveryengine_v1

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import PROJECT_ID, LOCATION, DATASTORE_ID, CREDENTIALS_FILE


def setup_credentials():
    """Setup credentials if specified in config."""
    if CREDENTIALS_FILE and 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
        credentials_path = Path(__file__).parent.parent / CREDENTIALS_FILE
        if credentials_path.exists():
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(credentials_path)
            print(f"Using credentials: {credentials_path}")


def create_data_store(project_id: str, location: str, datastore_id: str, chunk_size: int = 500):
    """Create a Vertex AI Search datastore with chunking configuration."""
    client = discoveryengine_v1.DataStoreServiceClient()

    parent = f"projects/{project_id}/locations/{location}/collections/default_collection"

    # Configure layout parsing for HTML documents
    default_parsing_config = discoveryengine_v1.DocumentProcessingConfig.ParsingConfig(
        layout_parsing_config=discoveryengine_v1.DocumentProcessingConfig.ParsingConfig.LayoutParsingConfig(
            enable_table_annotation=True,
            enable_image_annotation=True
        )
    )

    # Configure chunking for RAG
    chunking_config = discoveryengine_v1.DocumentProcessingConfig.ChunkingConfig(
        layout_based_chunking_config=discoveryengine_v1.DocumentProcessingConfig.ChunkingConfig.LayoutBasedChunkingConfig(
            chunk_size=chunk_size,
            include_ancestor_headings=True
        )
    )

    document_processing_config = discoveryengine_v1.DocumentProcessingConfig(
        default_parsing_config=default_parsing_config,
        chunking_config=chunking_config
    )

    data_store = discoveryengine_v1.DataStore(
        display_name=datastore_id,
        industry_vertical=discoveryengine_v1.IndustryVertical.GENERIC,
        content_config=discoveryengine_v1.DataStore.ContentConfig.CONTENT_REQUIRED,
        solution_types=[discoveryengine_v1.SolutionType.SOLUTION_TYPE_SEARCH],
        document_processing_config=document_processing_config
    )

    request = discoveryengine_v1.CreateDataStoreRequest(
        parent=parent,
        data_store=data_store,
        data_store_id=datastore_id
    )

    try:
        print(f'Creating datastore: {datastore_id}')
        print(f'   Type: Unstructured (for HTML/PDF with metadata)')
        print(f'   Parser: Layout Parser')
        print(f'      - Table annotation: ENABLED')
        print(f'      - Image annotation: ENABLED')
        print(f'   Chunking: ENABLED')
        print(f'      - Strategy: Layout-based')
        print(f'      - Chunk size: {chunk_size} tokens')
        print(f'      - Include ancestor headings: True')
        print(f'   Project: {project_id}')
        print(f'   Location: {location}')

        operation = client.create_data_store(request=request)

        print('Waiting for operation to complete...')
        response = operation.result(timeout=300)

        print(f'\nData store created successfully!')
        print(f'   Name: {response.name}')
        print(f'   Display name: {response.display_name}')

        return response

    except Exception as e:
        if 'ALREADY_EXISTS' in str(e) or 'already exists' in str(e):
            print(f'Data store {datastore_id} already exists')
            existing_name = f"{parent}/dataStores/{datastore_id}"
            print(f'   Name: {existing_name}')
            return None
        else:
            print(f'Error creating data store: {e}')
            raise


def main():
    parser = argparse.ArgumentParser(description='Create Vertex AI Search datastore')
    parser.add_argument('--chunk-size', type=int, default=500, help='Chunk size in tokens (default: 500)')
    args = parser.parse_args()

    setup_credentials()

    print(f'Creating datastore')
    print(f'   Datastore ID: {DATASTORE_ID}')
    print("=" * 60)

    create_data_store(PROJECT_ID, LOCATION, DATASTORE_ID, args.chunk_size)

    print(f'\nNext step: Import documents from GCS')
    print(f'   uv run python ingestion/04_import_documents.py')


if __name__ == '__main__':
    main()
