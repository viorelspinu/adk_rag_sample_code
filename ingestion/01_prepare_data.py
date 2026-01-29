#!/usr/bin/env python3
"""
Prepare HTML file for Vertex AI Search import.
Creates metadata.jsonl for the HTML file.

Usage:
    uv run python ingestion/01_prepare_data.py --input output/document.html
    uv run python ingestion/01_prepare_data.py --input output/document.html --title "My Document"
"""

import argparse
import json
import hashlib
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import BUCKET_NAME, SITE_PREFIX


def create_metadata_jsonl(html_file_path: Path, output_file: Path, title: str = None) -> tuple[str, str]:
    """Create metadata.jsonl file for import."""
    if not html_file_path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_file_path}")

    doc_id = hashlib.md5(str(html_file_path).encode('utf-8')).hexdigest()
    html_filename = html_file_path.name

    if not title:
        title = html_file_path.stem

    metadata = {
        "id": doc_id,
        "content": {
            "mimeType": "text/html",
            "uri": f"gs://{BUCKET_NAME}/{SITE_PREFIX}/html/{html_filename}"
        },
        "structData": {
            "title": title,
            "source_file": html_filename
        }
    }

    output_file.write_text(json.dumps(metadata, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"Created metadata.jsonl")
    print(f"   Document ID: {doc_id}")
    print(f"   HTML file: {html_filename}")
    print(f"   GCS URI: {metadata['content']['uri']}")

    return doc_id, html_filename


def main():
    parser = argparse.ArgumentParser(description='Prepare data for Vertex AI Search import')
    parser.add_argument('--input', required=True, help='Input HTML file path')
    parser.add_argument('--title', help='Document title (default: filename)')
    parser.add_argument('--output-dir', default='output', help='Output directory (default: output)')
    args = parser.parse_args()

    html_file = Path(args.input)
    if not html_file.exists():
        print(f"ERROR: HTML file not found: {html_file}")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    html_output_dir = output_dir / "html"
    html_output_dir.mkdir(exist_ok=True)

    metadata_file = output_dir / "metadata.jsonl"

    print(f"Preparing data for ingestion...")
    print(f"   HTML file: {html_file}")
    print("=" * 60)

    # Copy HTML file to output directory
    print(f"\nCopying HTML file to output directory...")
    html_output_file = html_output_dir / html_file.name
    if html_file.resolve() != html_output_file.resolve():
        shutil.copy2(html_file, html_output_file)
        print(f"   Copied to: {html_output_file}")
    else:
        print(f"   Already in output directory: {html_output_file}")

    # Create metadata
    print(f"\nCreating metadata.jsonl...")
    create_metadata_jsonl(html_output_file, metadata_file, args.title)

    print(f"\nPreparation complete!")
    print(f"   HTML file: {html_output_file}")
    print(f"   Metadata: {metadata_file}")
    print(f"\nNext step: Upload to GCS")
    print(f"   uv run python ingestion/02_upload_to_gcs.py")


if __name__ == '__main__':
    main()
