"""Warm the configured local model before a demo. No credentials are printed."""
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
if os.getenv('USE_MOCK_AI', 'false').lower() not in {'true','1','yes'}:
    try:
        result = httpx.post(os.getenv('OLLAMA_BASE_URL','http://127.0.0.1:11434').rstrip('/') + '/api/chat',
            json={'model':os.getenv('OLLAMA_MODEL','qwen3:4b'), 'messages':[], 'stream':False,
                  'keep_alive':int(os.getenv('OLLAMA_KEEP_ALIVE','-1')), 'options':{'num_ctx':4096}}, timeout=60)
        result.raise_for_status()
        print('Local model warmed and ready.')
    except (httpx.HTTPError, ValueError) as exc:
        print('Model warm-up failed (' + type(exc).__name__ + '). Open Ollama before using live ordering.')
