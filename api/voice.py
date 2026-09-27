"""Server-only speech providers. Audio is bounded and kept only in memory."""
import importlib.util
import io
import logging
import os
import threading

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

router = APIRouter(prefix='/voice')
MAX_AUDIO = 4 * 1024 * 1024
logger = logging.getLogger(__name__)
_whisper_model = None
_whisper_model_lock = threading.Lock()


def _transcribe_locally(audio_bytes: bytes) -> str:
    global _whisper_model
    import av
    import numpy as np
    from faster_whisper import WhisperModel

    if _whisper_model is None:
        with _whisper_model_lock:
            if _whisper_model is None:
                _whisper_model = WhisperModel(
                    os.getenv('WHISPER_MODEL', 'base.en'),
                    device='cpu',
                    compute_type='int8',
                    cpu_threads=max(1, min(os.cpu_count() or 4, 8)),
                )

    with av.open(io.BytesIO(audio_bytes)) as container:
        audio_stream = next((stream for stream in container.streams if stream.type == 'audio'), None)
        if audio_stream is None:
            raise ValueError('No audio stream')
        resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
        frames = []
        for frame in container.decode(audio=audio_stream.index):
            frames.extend(resampler.resample(frame))
        frames.extend(resampler.resample(None))

    if not frames:
        return ''
    waveform = np.concatenate([frame.to_ndarray().reshape(-1) for frame in frames]).astype(np.float32)
    waveform /= 32768.0
    segments, _ = _whisper_model.transcribe(
        waveform,
        language='en',
        beam_size=1,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    return ' '.join(segment.text.strip() for segment in segments).strip()[:500]

@router.get('/config')
async def config():
    cloud_enabled = os.getenv('USE_CLOUD_VOICE', 'true').lower().strip() in {'true', '1', 'yes'}
    dg_key = os.getenv('DEEPGRAM_API_KEY')
    el_key = os.getenv('ELEVENLABS_API_KEY')
    has_dg = cloud_enabled and bool(dg_key)
    has_el = cloud_enabled and bool(el_key)
    return {
        'stt': has_dg,
        'local_stt': not has_dg and importlib.util.find_spec('faster_whisper') is not None,
        'tts': has_el,
    }

DEEPGRAM_KEYTERMS = [
    'pastilla', 'Fish pastilla', 'briouates', 'Beef briouates', 'croissant',
    'tajine', 'bouskoura', 'pitta', 'mutabel', 'ezme', 'Acili Ezme',
    'Baba Ghanouch', 'carpaccio', 'parmigiana', 'Yony burger', 'dirhams',
    'hot drink', 'cold drink', 'hot beverage', 'cold beverage',
]

@router.post('/transcribe')
async def transcribe(request: Request):
    mime = request.headers.get('content-type', '').split(';')[0]
    if mime not in {'audio/webm', 'audio/ogg', 'audio/mp4', 'audio/wav'}:
        raise HTTPException(415, 'Unsupported audio format')
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_AUDIO: raise HTTPException(413, 'Audio recording is too large')
    if not body: raise HTTPException(400, 'Empty audio')
    cloud_enabled = os.getenv('USE_CLOUD_VOICE', 'true').lower().strip() in {'true', '1', 'yes'}
    key = os.getenv('DEEPGRAM_API_KEY')
    if cloud_enabled and key:
        try:
            params = [
                ('model', 'nova-3'),
                ('language', 'en'),
                ('smart_format', 'true'),
            ] + [('keyterm', term) for term in DEEPGRAM_KEYTERMS]
            async with httpx.AsyncClient(timeout=20) as client:
                result = await client.post('https://api.deepgram.com/v1/listen',
                    params=params,
                    headers={'Authorization': f'Token {key}', 'Content-Type': request.headers['content-type']},
                    content=bytes(body))
                result.raise_for_status()
                text = result.json()['results']['channels'][0]['alternatives'][0]['transcript']
                return {'text': text[:500]}
        except (httpx.HTTPError, KeyError, ValueError, IndexError) as err:
            logger.warning('Deepgram transcription failed, falling back if available: %s', type(err).__name__)
            if importlib.util.find_spec('faster_whisper') is not None:
                try:
                    text = await run_in_threadpool(_transcribe_locally, bytes(body))
                    return {'text': text}
                except Exception:
                    pass
            raise HTTPException(503, 'Speech recognition is unavailable. Retry or use browser speech.') from None

    if importlib.util.find_spec('faster_whisper') is None:
        raise HTTPException(503, 'Local speech recognition is not installed. Type your order or install faster-whisper.')
    try:
        text = await run_in_threadpool(_transcribe_locally, bytes(body))
        return {'text': text}
    except Exception as error:
        logger.warning('Local transcription failed: %s', type(error).__name__)
        raise HTTPException(503, 'Local speech recognition failed. Please repeat or type your order.') from None

class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2500)

@router.post('/speak')
async def speak(request: SpeechRequest):
    cloud_enabled = os.getenv('USE_CLOUD_VOICE', 'true').lower().strip() in {'true', '1', 'yes'}
    key = os.getenv('ELEVENLABS_API_KEY')
    if not (cloud_enabled and key):
        raise HTTPException(503, 'Cloud voice is disabled. Use browser speech.')
    voice = os.getenv('ELEVENLABS_VOICE_ID', 'JBFqnCBsd6RMkjVDRZzb')
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            result = await client.post(f'https://api.elevenlabs.io/v1/text-to-speech/{voice}',
                headers={'xi-api-key': key},
                json={'text': request.text, 'model_id': 'eleven_flash_v2_5'})
            result.raise_for_status()
            return Response(result.content, media_type='audio/mpeg', headers={'Cache-Control': 'no-store'})
    except httpx.HTTPError:
        raise HTTPException(503, 'Cloud voice is unavailable. Browser voice can be used.') from None
