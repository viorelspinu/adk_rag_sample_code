"""
Vertex AI Search tool for RAG retrieval.

This tool searches a Vertex AI Search datastore and returns chunk content
with metadata for RAG-based question answering.
"""

import re
import logging
from google.cloud import discoveryengine_v1

from src import config

logger = logging.getLogger(__name__)


def extract_page_from_content(content: str) -> int | None:
    """Extract page number from chunk content text using regex.

    Looks for patterns like "## Page X" or "Page X" in the content.
    Returns the first page number found, or None if not found.
    """
    if not content:
        return None

    patterns = [
        r'##\s*Page\s+(\d+)',
        r'Page\s+(\d+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                continue

    return None


def search(query: str) -> dict:
    """Search the document database for information.

    This tool searches the configured Vertex AI Search datastore and returns
    full chunk content with metadata. Use this tool to find relevant information
    before answering questions.

    Args:
        query: The search query to find relevant information.

    Returns:
        A dictionary containing:
        - chunks: List of chunks with full content, title, URI, page number, and document ID
        - query: The search query that was executed
        - total_results: Total number of chunks found
    """
    try:
        client = discoveryengine_v1.SearchServiceClient()

        serving_config = client.serving_config_path(
            project=config.PROJECT_ID,
            location=config.LOCATION,
            data_store=config.DATASTORE_ID,
            serving_config="default_config",
        )

        content_search_spec = discoveryengine_v1.SearchRequest.ContentSearchSpec(
            snippet_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.SnippetSpec(
                return_snippet=True,
                max_snippet_count=5
            ),
            search_result_mode=discoveryengine_v1.SearchRequest.ContentSearchSpec.SearchResultMode.CHUNKS,
            chunk_spec=discoveryengine_v1.SearchRequest.ContentSearchSpec.ChunkSpec()
        )

        request = discoveryengine_v1.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=10,
            content_search_spec=content_search_spec
        )

        logger.info(f"Searching for: {query}")
        response = client.search(request=request)

        chunks = []
        for result in response.results:
            doc = result.document
            chunk = result.chunk

            if not chunk.content:
                continue

            struct = dict(doc.struct_data) if doc.struct_data else {}
            derived = dict(doc.derived_struct_data) if doc.derived_struct_data else {}

            page_number = extract_page_from_content(chunk.content)

            chunks.append({
                'content': chunk.content,
                'title': struct.get('title') or derived.get('title'),
                'uri': struct.get('uri') or struct.get('link') or derived.get('link'),
                'document_id': doc.id if doc.id else None,
                'page': page_number
            })

        result = {
            'chunks': chunks,
            'query': query,
            'total_results': len(chunks)
        }

        logger.info(f"Found {len(chunks)} chunks for query: {query}")
        return result

    except Exception as e:
        logger.error(f"Error in search: {e}", exc_info=True)
        return {
            'chunks': [],
            'query': query,
            'total_results': 0,
            'error': str(e)
        }
