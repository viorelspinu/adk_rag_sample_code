#!/usr/bin/env python3
"""
Upload HTML file and metadata to Google Cloud Storage.

Usage:
    uv run python ingestion/02_upload_to_gcs.py
    uv run python ingestion/02_upload_to_gcs.py --output-dir custom_output
"""

import argparse
import sys
import os
from pathlib import Path
from google.cloud import storage

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import PROJECT_ID, BUCKET_NAME, REGION, SITE_PREFIX, CREDENTIALS_FILE


def setup_credentials():
    """Setup credentials if specified in config."""
    if CREDENTIALS_FILE and 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
        credentials_path = Path(__file__).parent.parent / CREDENTIALS_FILE
        if credentials_path.exists():
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(credentials_path)
            print(f"Using credentials: {credentials_path}")
        else:
            print(f"Warning: Credentials file not found: {credentials_path}")
            print("   Using Application Default Credentials")


def create_bucket_if_not_exists(storage_client, bucket_name: str, region: str):
    """Create bucket if it doesn't exist."""
    try:
        bucket = storage_client.get_bucket(bucket_name)
        print(f'Bucket {bucket_name} already exists')
        return bucket
    except Exception:
        print(f'Creating bucket {bucket_name} in region {region}...')
        bucket = storage_client.create_bucket(bucket_name, location=region)
        print(f'Bucket {bucket_name} created successfully')
        return bucket


def upload_file_to_gcs(bucket, source_file_path: str, destination_blob_name: str) -> str:
    """Upload a file to GCS."""
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_path)
    print(f'  Uploaded: {destination_blob_name}')
    return f'gs://{bucket.name}/{destination_blob_name}'


def main():
    parser = argparse.ArgumentParser(description='Upload files to Google Cloud Storage')
    parser.add_argument('--output-dir', default='output', help='Output directory with prepared files')
    args = parser.parse_args()

    setup_credentials()

    output_dir = Path(args.output_dir)
    html_dir = output_dir / 'html'
    metadata_file = output_dir / 'metadata.jsonl'

    if not html_dir.exists() or not metadata_file.exists():
        print(f'ERROR: Prepared data not found')
        print(f'  Expected HTML dir: {html_dir}')
        print(f'  Expected metadata file: {metadata_file}')
        print(f'Please run 01_prepare_data.py first')
        sys.exit(1)

    html_files = list(html_dir.glob('*.html'))
    if not html_files:
        print(f'ERROR: No HTML files found in {html_dir}')
        sys.exit(1)

    print(f'Uploading {len(html_files)} HTML file(s) + metadata to GCS...')
    print(f'   Project: {PROJECT_ID}')
    print(f'   Bucket: {BUCKET_NAME}')
    print(f'   Prefix: {SITE_PREFIX}/')
    print("=" * 60)

    storage_client = storage.Client(project=PROJECT_ID)
    bucket = create_bucket_if_not_exists(storage_client, BUCKET_NAME, REGION)

    site_prefix = f'{SITE_PREFIX}/'

    # Clean old files
    print(f'\nCleaning old files from bucket (prefix: {site_prefix})...')
    blobs_to_delete = list(bucket.list_blobs(prefix=f'{site_prefix}html/'))
    metadata_blob = bucket.blob(f'{site_prefix}metadata.jsonl')
    if metadata_blob.exists():
        blobs_to_delete.append(metadata_blob)

    deleted_count = 0
    for blob in blobs_to_delete:
        if blob.exists():
            blob.delete()
            deleted_count += 1

    if deleted_count > 0:
        print(f'   Deleted {deleted_count} old files')
    else:
        print(f'   No old files to delete')

    # Upload HTML files
    print(f'\nUploading HTML files...')
    for html_file in html_files:
        destination_blob = f'{site_prefix}html/{html_file.name}'
        upload_file_to_gcs(bucket, str(html_file), destination_blob)

    # Upload metadata
    print(f'\nUploading metadata file...')
    metadata_uri = upload_file_to_gcs(bucket, str(metadata_file), f'{site_prefix}metadata.jsonl')

    print(f'\nUpload complete!')
    print(f'   HTML files: {len(html_files)} file(s) uploaded to gs://{BUCKET_NAME}/{site_prefix}html/')
    print(f'   Metadata: {metadata_uri}')
    print(f'\nNext step: Create data store')
    print(f'   uv run python ingestion/03_create_datastore.py')


if __name__ == '__main__':
    main()
