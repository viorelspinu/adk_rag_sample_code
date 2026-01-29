#!/usr/bin/env python3
"""
RAG Agent using Google ADK with Vertex AI Search.

This module provides a simple RAG agent that:
1. Takes user questions
2. Searches a Vertex AI Search datastore
3. Returns answers grounded in the document content

Usage:
    uv run python src/agent.py
    uv run python src/agent.py --question "What is X?"
"""

import argparse
import asyncio
import os
import logging
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src import config
from src.search_tool import search
from src.prompts import get_instruction

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def setup_credentials():
    """Setup Google Cloud credentials and environment variables."""
    # Set credentials if specified
    if config.CREDENTIALS_FILE and 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ:
        credentials_path = Path(__file__).parent.parent / config.CREDENTIALS_FILE
        if credentials_path.exists():
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(credentials_path)
            logger.info(f"Using credentials: {credentials_path}")
        else:
            logger.warning(f"Credentials file not found: {credentials_path}")

    # Required environment variables for Google ADK
    os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = 'TRUE'
    os.environ['GOOGLE_CLOUD_PROJECT'] = config.PROJECT_ID
    os.environ['GOOGLE_CLOUD_LOCATION'] = config.LOCATION


def create_agent() -> LlmAgent:
    """Create and configure the RAG agent."""
    setup_credentials()

    agent = LlmAgent(
        model=config.MODEL,
        name="rag_agent",
        instruction=get_instruction(),
        tools=[search]
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
    tool_calls = []

    for event in events:
        # Track tool calls for debugging
        if hasattr(event, 'content') and event.content:
            if hasattr(event.content, 'parts'):
                for part in event.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        func_name = part.function_call.name
                        func_args = dict(part.function_call.args) if part.function_call.args else {}
                        tool_calls.append({'name': func_name, 'args': func_args})

        # Get final response
        if event.is_final_response():
            full_response = event.content.parts[0].text
            print(full_response)

    # Print tool call summary
    if tool_calls:
        print(f'\n[Search tool called {len(tool_calls)} time(s)]')
        for tc in tool_calls:
            if tc['args'].get('query'):
                print(f'  Query: "{tc["args"]["query"]}"')

    print()
    return full_response


async def interactive_mode():
    """Run the agent in interactive mode."""
    print(f'RAG Agent initialized')
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
    print(f'RAG Agent - Single Query Mode')
    print(f'   Project: {config.PROJECT_ID}')
    print(f'   Datastore: {config.DATASTORE_ID}')
    print("=" * 60)

    agent = create_agent()
    session_service = InMemorySessionService()
    session = await session_service.create_session(user_id="user", app_name="rag_app")

    await query_agent(agent, question, session_service, session)


def main():
    parser = argparse.ArgumentParser(description='RAG Agent with Vertex AI Search')
    parser.add_argument('--question', '-q', type=str, help='Run a single question and exit')
    args = parser.parse_args()

    if args.question:
        asyncio.run(run_single_question(args.question))
    else:
        asyncio.run(interactive_mode())


if __name__ == '__main__':
    main()
