#!/usr/bin/env python3
"""
Import documents from GCS to Vertex AI Search datastore.

Usage:
    uv run python ingestion/04_import_documents.py
"""

import os
import sys
from pathlib import Path
from google.cloud import discoveryengine_v1

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import PROJECT_ID, LOCATION, DATASTORE_ID, BUCKET_NAME, SITE_PREFIX, CREDENTIALS_FILE


def setup_credentials():
    """Setup credentials if specified in config."""
    if CREDENTIALS_FILE and 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
        credentials_path = Path(__file__).parent.parent / CREDENTIALS_FILE
        if credentials_path.exists():
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(credentials_path)
            print(f"Using credentials: {credentials_path}")


def import_documents(project_id: str, location: str, datastore_id: str, bucket_name: str, site_prefix: str):
    """Import documents from GCS to the datastore."""
    client = discoveryengine_v1.DocumentServiceClient()

    parent = (
        f"projects/{project_id}/locations/{location}/"
        f"collections/default_collection/dataStores/{datastore_id}/"
        f"branches/default_branch"
    )

    gcs_uri = f"gs://{bucket_name}/{site_prefix}/metadata.jsonl"

    request = discoveryengine_v1.ImportDocumentsRequest(
        parent=parent,
        gcs_source=discoveryengine_v1.GcsSource(
            input_uris=[gcs_uri],
            data_schema="document"
        ),
        reconciliation_mode=discoveryengine_v1.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL
    )

    print(f'Starting document import...')
    print(f'   Data store: {datastore_id}')
    print(f'   Source: {gcs_uri}')
    print(f'   Schema: document (HTML files referenced by URI with metadata)')
    print(f'\nThis may take 30 minutes to 2 hours depending on the number of documents.')

    try:
        operation = client.import_documents(request=request)

        print(f'\nImport operation started!')
        print(f'   Operation name: {operation.operation.name}')

        # Save operation name for status checking
        operation_file = Path(__file__).parent / '.last_import_operation'
        with open(operation_file, 'w') as f:
            f.write(operation.operation.name)

        print(f'\nTo check import status:')
        print(f'   - Check the GCP Console: https://console.cloud.google.com/gen-app-builder/data-stores?project={project_id}')
        print(f'\nOnce import is complete, test the agent:')
        print(f'   uv run python src/agent.py')

        return operation

    except Exception as e:
        print(f'Error importing documents: {e}')
        raise


def main():
    setup_credentials()

    print(f'Importing documents to datastore')
    print(f'   Datastore: {DATASTORE_ID}')
    print("=" * 60)

    import_documents(PROJECT_ID, LOCATION, DATASTORE_ID, BUCKET_NAME, SITE_PREFIX)


if __name__ == '__main__':
    main()
