"""Check the local Ollama runtime and a full-catalog recommendation."""
import asyncio
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / '.env')

from api.catalog import CATALOG
from api.recommendation import recommend_with_ollama


async def main():
    base_url = os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/')
    model = os.getenv('OLLAMA_MODEL', 'edtorre/qwen3.5-hermes:latest')
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            version_response = await client.get(f'{base_url}/api/version')
            version_response.raise_for_status()
            tags_response = await client.get(f'{base_url}/api/tags')
            tags_response.raise_for_status()
        installed = {entry['name'] for entry in tags_response.json().get('models', [])}
        print(f'Ollama runtime: {version_response.json().get("version", "available")}')
        if model not in installed:
            print(f'Model is not installed: {model}')
            print(f'Install it with: ollama pull {model}')
            return 1
        print(f'Local model installed: {model}')
        selection = await recommend_with_ollama(
            'Two large coffees without sugar and one croissant', CATALOG,
        )
        if not selection:
            print('Full-catalog structured recommendation failed.')
            return 1
        if len(selection['basket']) != 2 or selection['total_mad'] != 46:
            print('Local model did not return both items with the expected validated total.')
            return 1
        print(
            'Recommendation:', selection['restaurant']['name'],
            f"{len(selection['basket'])} items, {selection['total_mad']:g} MAD",
        )
        return 0
    except (httpx.HTTPError, KeyError, ValueError) as error:
        print(f'Ollama check failed: {type(error).__name__}')
        return 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
