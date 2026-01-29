#!/usr/bin/env python3
"""
Preprocess PDF files for Vertex AI Search ingestion.
Handles tables, text extraction, and converts to HTML format.

Usage:
    uv run python ingestion/00_preprocess.py --input /path/to/file.pdf --output /path/to/output.html
    uv run python ingestion/00_preprocess.py --input /path/to/file.pdf --output /path/to/output_dir --split-pages
"""

import argparse
import sys
from pathlib import Path
import logging
import html as html_module
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def normalize_word_breaks(text: str) -> str:
    """Remove spaces and hyphens that appear to be line-break artifacts in the middle of words.

    This fixes cases like:
    - "word-\\nword" -> "wordword" (hyphenated line breaks)
    - "com - petence" -> "competence" (space + hyphen + space)
    """
    if not text:
        return text

    # Fix hyphenated word breaks (word-hyphen-space/newline-word)
    # Pattern 1: "word - word" -> "wordword" (space-hyphen-space)
    text = re.sub(r'(\w+)\s+-\s+(\w+)', r'\1\2', text)

    # Pattern 2: "word-\nword" or "word- word" -> "wordword"
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)

    # Clean up excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text


def extract_text_and_tables(pdf_path: Path) -> list[dict]:
    """Extract text and tables from PDF using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not installed. Install with: uv add pdfplumber")
        sys.exit(1)

    pages_data = []

    with pdfplumber.open(pdf_path) as pdf:
        logger.info(f"Processing {len(pdf.pages)} pages...")

        for page_num, page in enumerate(pdf.pages, 1):
            page_data = {
                'page_num': page_num,
                'text': '',
                'tables': []
            }

            # Extract tables
            tables = page.extract_tables()
            if tables:
                logger.info(f"  Page {page_num}: Found {len(tables)} table(s)")
                for table in tables:
                    page_data['tables'].append(table)

            # Extract text
            text = page.extract_text()
            if text:
                # Normalize word breaks
                text = normalize_word_breaks(text.strip())
                page_data['text'] = text

            pages_data.append(page_data)

    return pages_data


def table_to_html(table: list[list]) -> str:
    """Convert a table (list of lists) to HTML table."""
    if not table or not table[0]:
        return ""

    html_lines = ['<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; margin: 10px 0;">']

    for row_idx, row in enumerate(table):
        html_lines.append('  <tr>')
        for cell in row:
            cell_text = str(cell).strip() if cell else ""
            cell_text_escaped = html_module.escape(cell_text)
            tag = 'th' if row_idx == 0 else 'td'
            html_lines.append(f'    <{tag}>{cell_text_escaped}</{tag}>')
        html_lines.append('  </tr>')

    html_lines.append('</table>')
    return '\n'.join(html_lines)


def pages_to_html(pages_data: list[dict], title: str = "Document", split_pages: bool = False) -> list[str]:
    """Convert pages data to HTML format."""
    html_parts = []

    if split_pages:
        # Create separate HTML file for each page
        for page_data in pages_data:
            page_html = []
            page_html.append(f'<html><head><title>{title} - Page {page_data["page_num"]}</title></head><body>')
            page_html.append(f'<h1>{title}</h1>')
            page_html.append(f'<h2>Page {page_data["page_num"]}</h2>')

            if page_data['text']:
                text_escaped = html_module.escape(page_data['text'])
                page_html.append(f'<div class="text-content">')
                page_html.append(f'<pre style="white-space: pre-wrap; font-family: Arial, sans-serif;">{text_escaped}</pre>')
                page_html.append('</div>')

            if page_data['tables']:
                page_html.append('<div class="tables">')
                for table in page_data['tables']:
                    page_html.append(table_to_html(table))
                page_html.append('</div>')

            page_html.append('</body></html>')
            html_parts.append('\n'.join(page_html))
    else:
        # Create single HTML file with all pages
        html_parts.append(f'<html><head><title>{title}</title></head><body>')
        html_parts.append(f'<h1>{title}</h1>')

        for page_data in pages_data:
            html_parts.append(f'<div class="page" data-page="{page_data["page_num"]}">')
            html_parts.append(f'<h2>Page {page_data["page_num"]}</h2>')

            if page_data['text']:
                text_escaped = html_module.escape(page_data['text'])
                html_parts.append('<div class="text-content">')
                html_parts.append(f'<pre style="white-space: pre-wrap; font-family: Arial, sans-serif;">{text_escaped}</pre>')
                html_parts.append('</div>')

            if page_data['tables']:
                html_parts.append('<div class="tables">')
                for table_idx, table in enumerate(page_data['tables'], 1):
                    html_parts.append(f'<div class="table" data-table="{table_idx}">')
                    html_parts.append(table_to_html(table))
                    html_parts.append('</div>')
                html_parts.append('</div>')

            html_parts.append('</div>')
            html_parts.append('<hr style="margin: 20px 0;">')

        html_parts.append('</body></html>')

    return html_parts


def main():
    parser = argparse.ArgumentParser(description='Preprocess PDF for Vertex AI Search ingestion')
    parser.add_argument('--input', required=True, help='Input PDF file path')
    parser.add_argument('--output', required=True, help='Output HTML file path (or directory if --split-pages)')
    parser.add_argument('--split-pages', action='store_true', help='Split into separate HTML files per page')
    parser.add_argument('--title', help='Document title (default: filename)')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    if not args.title:
        args.title = input_path.stem

    logger.info(f"Extracting text and tables from: {input_path}")
    pages_data = extract_text_and_tables(input_path)

    total_tables = sum(len(page['tables']) for page in pages_data)
    pages_with_text = sum(1 for page in pages_data if page['text'])
    logger.info(f"Extracted {len(pages_data)} pages with {total_tables} total tables")
    logger.info(f"Pages with text: {pages_with_text}")

    if pages_with_text == 0:
        logger.warning("No text extracted from PDF! Check if PDF is image-based or encrypted.")

    output_path = Path(args.output)

    if args.split_pages:
        output_path.mkdir(parents=True, exist_ok=True)
        html_parts = pages_to_html(pages_data, args.title, split_pages=True)

        for page_data, html_content in zip(pages_data, html_parts):
            page_output = output_path / f"page_{page_data['page_num']:03d}.html"
            page_output.write_text(html_content, encoding='utf-8')
            logger.info(f"Saved: {page_output}")

        logger.info(f"\nProcessed {len(html_parts)} pages to {output_path}")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        html_parts = pages_to_html(pages_data, args.title, split_pages=False)
        html_content = '\n'.join(html_parts)

        output_path.write_text(html_content, encoding='utf-8')
        logger.info(f"\nSaved processed PDF to: {output_path}")
        logger.info(f"   Pages: {len(pages_data)}")
        logger.info(f"   Tables: {total_tables}")
        logger.info(f"   Output size: {len(html_content)} characters")

    print(f"\nNext step: Prepare metadata")
    print(f"   uv run python ingestion/01_prepare_data.py --input {args.output}")


if __name__ == '__main__':
    main()
