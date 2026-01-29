#!/usr/bin/env python3
"""
RAG Agent using Google ADK with built-in VertexAiSearchTool.

This agent uses the built-in VertexAiSearchTool which handles all search
logic automatically - no custom search code needed.

Usage:
    uv run python src/agent_with_built_in_search_tool.py
    uv run python src/agent_with_built_in_search_tool.py --question "What is X?"

Docs: https://google.github.io/adk-docs/tools/google-cloud/vertex-ai-search/
"""

import argparse
import asyncio
import os
import logging
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import VertexAiSearchTool
from google.genai import types

from src import config
from src.prompts import get_instruction

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def setup_credentials():
    """Setup Google Cloud credentials and environment variables."""
    if config.CREDENTIALS_FILE and 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
        credentials_path = Path(__file__).parent.parent / config.CREDENTIALS_FILE
        if credentials_path.exists():
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(credentials_path)
            logger.info(f"Using credentials: {credentials_path}")
        else:
            raise RuntimeError(f"Credentials file not found: {credentials_path}")

    # Required environment variables for Google ADK with Vertex AI
    os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = 'TRUE'
    os.environ['GOOGLE_CLOUD_PROJECT'] = config.PROJECT_ID
    os.environ['GOOGLE_CLOUD_LOCATION'] = config.LOCATION


def get_datastore_path() -> str:
    """Build the full datastore path required by VertexAiSearchTool."""
    return (
        f"projects/{config.PROJECT_ID}/locations/{config.LOCATION}/"
        f"collections/default_collection/dataStores/{config.DATASTORE_ID}"
    )


def create_agent() -> LlmAgent:
    """Create and configure the RAG agent with built-in VertexAiSearchTool."""
    setup_credentials()

    datastore_path = get_datastore_path()
    logger.info(f"Using datastore: {datastore_path}")

    # Built-in tool - no custom search code needed!
    vertex_search_tool = VertexAiSearchTool(data_store_id=datastore_path)

    agent = LlmAgent(
        model=config.MODEL,
        name="rag_agent_builtin",
        instruction=get_instruction(),
        tools=[vertex_search_tool]  # Note: VertexAiSearchTool must be used alone
    )

    return agent


async def query_agent(agent: LlmAgent, question: str, session_service: InMemorySessionService, session) -> str:
    """Query the agent with a question and return the response."""
    runner = Runner(
        app_name="rag_app",
        agent=agent,
        session_service=session_service
    )

    print(f'\nQuestion: {question}')
    print('Answer: ', end='', flush=True)

    content = types.Content(role='user', parts=[types.Part(text=question)])

    events = runner.run(
        user_id="user",
        session_id=session.id,
        new_message=content
    )

    full_response = ''
    grounding_metadata = None

    for event in events:
        if event.is_final_response():
            full_response = event.content.parts[0].text
            print(full_response)

            # Capture grounding metadata if available
            if hasattr(event, 'grounding_metadata') and event.grounding_metadata:
                grounding_metadata = event.grounding_metadata

    # Print grounding information
    if grounding_metadata:
        print(f'\n--- Grounding Info ---')

        # Show retrieval queries
        if hasattr(grounding_metadata, 'retrieval_queries') and grounding_metadata.retrieval_queries:
            print(f'Queries executed:')
            for q in grounding_metadata.retrieval_queries:
                print(f'  - "{q}"')

        # Show source documents
        if hasattr(grounding_metadata, 'grounding_chunks') and grounding_metadata.grounding_chunks:
            print(f'Sources ({len(grounding_metadata.grounding_chunks)} chunks):')
            for i, chunk in enumerate(grounding_metadata.grounding_chunks, 1):
                title = None
                uri = None
                if hasattr(chunk, 'retrieved_context') and chunk.retrieved_context:
                    ctx = chunk.retrieved_context
                    title = getattr(ctx, 'title', None)
                    uri = getattr(ctx, 'uri', None)
                if title:
                    print(f'  {i}. {title}')
                if uri:
                    print(f'     URI: {uri}')

    print()
    return full_response


async def interactive_mode():
    """Run the agent in interactive mode."""
    print(f'RAG Agent (Built-in VertexAiSearchTool)')
    print(f'   Project: {config.PROJECT_ID}')
    print(f'   Datastore: {config.DATASTORE_ID}')
    print(f'   Model: {config.MODEL}')

    agent = create_agent()
    session_service = InMemorySessionService()
    session = await session_service.create_session(user_id="user", app_name="rag_app")

    print('   Ready!')
    print("=" * 60)
    print('\nAsk questions (type "quit" to exit):\n')

    while True:
        try:
            question = input('> ')
            if question.lower() in ['quit', 'exit', 'q']:
                print('Goodbye!')
                break

            if not question.strip():
                continue

            await query_agent(agent, question, session_service, session)

        except KeyboardInterrupt:
            print('\nGoodbye!')
            break
        except Exception as e:
            print(f'\nError: {e}\n')


async def run_single_question(question: str):
    """Run a single question and exit."""
    print(f'RAG Agent (Built-in VertexAiSearchTool) - Single Query')
    print(f'   Project: {config.PROJECT_ID}')
    print(f'   Datastore: {config.DATASTORE_ID}')
    print("=" * 60)

    agent = create_agent()
    session_service = InMemorySessionService()
    session = await session_service.create_session(user_id="user", app_name="rag_app")

    await query_agent(agent, question, session_service, session)


def main():
    parser = argparse.ArgumentParser(description='RAG Agent with built-in VertexAiSearchTool')
    parser.add_argument('--question', '-q', type=str, help='Run a single question and exit')
    args = parser.parse_args()

    if args.question:
        asyncio.run(run_single_question(args.question))
    else:
        asyncio.run(interactive_mode())


if __name__ == '__main__':
    main()
