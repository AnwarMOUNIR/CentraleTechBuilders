import asyncio
import json
from copy import deepcopy
from types import SimpleNamespace
import pytest
import httpx
from fastapi.testclient import TestClient
from api.main import app
from api.catalog import CATALOG, DEMO_MENU
from api.logic import next_step
from api.interpreter import interpret
from api.recommendation import recommend_order, recommend_with_ollama

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('USE_MOCK_AI', 'true')
    return TestClient(app)

def order(client, text, previous=None, restaurant_id='demo'):
    previous = previous or {'state': 'REQUEST', 'basket': [], 'pending': None}
    response = client.post('/interpret', json={**{k: previous[k] for k in ('state', 'basket', 'pending')},
                                             'text': text, 'restaurant_id': restaurant_id})
    assert response.status_code == 200
    return response.json()

def test_full_voice_script_and_negated_confirmation(client):
    first = order(client, 'One large coffee without sugar')
    assert first['total_mad'] == 18
    assert 'No sugar' in first['reply_text'] and '18 dirhams' in first['reply_text']
    changed = order(client, 'Make that two coffees', first)
    assert changed['total_mad'] == 36
    assert changed['basket'][0]['modifier_ids'] == ['large', 'no_sugar']
    assert order(client, "don't confirm", changed)['state'] != 'CONFIRMED'
    confirmed = order(client, 'confirm order', changed)
    assert confirmed['state'] == 'CONFIRMED'
    assert 'Simulated' in confirmed['reply_text'] and '36 dirhams' in confirmed['reply_text']
    assert order(client, 'One croissant', confirmed)['total_mad'] == 10

def test_missing_quantity_and_change_prompt(client):
    first = order(client, 'coffee')
    assert first['state'] == 'CLARIFY'
    second = order(client, 'two', first)
    assert second['total_mad'] == 24
    prompt = order(client, 'change', second)
    assert prompt['pending']['missing_field'] == 'change'
    assert order(client, 'three', prompt)['total_mad'] == 36

def test_menu_and_all_restaurants(client):
    catalog = client.get('/catalog').json()
    assert len(catalog) == 7
    assert [restaurant['name'] for restaurant in catalog] == [
        'ClearOrder Demo Cafe', 'Lilac Kitchen', 'Green Spoon Cafe',
        'Cornerstone Grill', 'Little Olive Kitchen', 'Cedar Spice House',
        'Orange Grove Kitchen',
    ]
    for r in catalog:
        product = r['menu'][0]
        result = order(client, 'one ' + product['name'], restaurant_id=r['id'])
        assert result['total_mad'] == product['base_price_mad']
    assert 'Coffee' in order(client, 'help')['reply_text']

def test_recommendation_prefers_menu_covering_all_requested_items():
    result = recommend_order('I want coffee and a croissant', CATALOG)
    assert result['restaurant']['id'] == 'demo'
    assert {line['product_id'] for line in result['basket']} == {'coffee', 'croissant'}
    assert result['total_mad'] == 22

def test_recommendation_uses_lowest_listed_price_for_shared_item():
    result = recommend_order('orange juice', CATALOG)
    assert result['restaurant']['id'] == 'lecheria_bouskoura'
    assert result['total_mad'] == 13

def test_recommendation_requires_supported_options():
    result = recommend_order('large coffee without sugar', CATALOG)
    assert result['restaurant']['id'] == 'demo'
    assert result['basket'][0]['modifier_ids'] == ['large', 'no_sugar']

def test_recommendation_ignores_unrecognized_menu_request():
    assert recommend_order('I want a dragonfruit smoothie', CATALOG) is None

def test_ollama_recommendation_receives_all_menus_and_reprices(monkeypatch):
    from api import recommendation
    payload = {
        'restaurant_id': 'demo',
        'items': [
            {'product_id': 'coffee', 'quantity': 2, 'modifier_ids': ['large', 'no_sugar']},
            {'product_id': 'croissant', 'quantity': 1, 'modifier_ids': []},
        ],
        'unmatched_items': [],
    }
    captured = {}

    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return {'message': {'content': json.dumps(payload)}}
    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, json):
            captured.update(json)
            return FakeResponse()

    monkeypatch.setattr(recommendation.httpx, 'AsyncClient', lambda **kwargs: FakeClient())
    result = asyncio.run(recommend_with_ollama('two big coffees with no sugar and a croissant', CATALOG))
    assert result['restaurant']['id'] == 'demo'
    assert result['total_mad'] == 46
    assert [line['product_id'] for line in result['basket']] == ['coffee', 'croissant']
    prompt = captured['messages'][0]['content']
    assert 'Coffee' in prompt and 'Croissant' in prompt
    assert 'Fish pastilla' not in prompt  # Only retrieved candidates go to Qwen.

def test_recommend_endpoint_returns_priced_review_basket(client):
    response = client.post('/recommend', json={'text': 'two large coffees without sugar and a croissant'})
    assert response.status_code == 200
    result = response.json()
    assert result['restaurant_id'] == 'demo'
    assert result['state'] == 'REVIEW'
    assert result['total_mad'] == 46
    assert result['basket'][0]['modifier_ids'] == ['large', 'no_sugar']
    assert 'This is only a proposal' in result['reply_text']
    assert 'two large coffees without sugar' in result['reply_text']
    assert 'one croissant' in result['reply_text']
    assert 'say no, cancel' in result['reply_text']

def test_recommend_endpoint_recovers_items_omitted_by_local_model(client, monkeypatch):
    from api import main
    complete = recommend_order('two large coffees without sugar and one croissant', CATALOG)
    partial = {**complete, 'basket': complete['basket'][:1], 'total_mad': complete['basket'][0]['line_total_mad']}
    async def omit_item(*args, **kwargs): return partial
    monkeypatch.setenv('USE_MOCK_AI', 'false')
    monkeypatch.setattr(main, 'recommend_with_ollama', omit_item)
    response = client.post('/recommend', json={'text': 'two large coffees without sugar and one croissant'})
    result = response.json()
    assert response.status_code == 200
    assert len(result['basket']) == 2
    assert result['total_mad'] == 46

def test_reprice_and_deduplicate_modifiers():
    basket = [{'product_id': 'coffee', 'quantity': 1, 'modifier_ids': ['large', 'large'], 'line_total_mad': 1}]
    original = deepcopy(basket)
    result = next_step({'intent': 'confirm'}, basket, 'REVIEW', DEMO_MENU)
    assert result['total_mad'] == 18
    assert basket == original

def test_pending_cannot_confirm():
    basket = [{'product_id': 'coffee', 'quantity': 1, 'modifier_ids': [], 'line_total_mad': 12}]
    result = next_step({'intent': 'confirm'}, basket, 'REVIEW', DEMO_MENU, {'missing_field': 'change'})
    assert result['state'] == 'CLARIFY'

@pytest.mark.parametrize('text', ['no', 'no cancel', 'no thanks', "don't confirm", 'do not confirm', 'not now'])
def test_negative_confirmation_discards_review_order(client, text):
    reviewed = order(client, 'One coffee')
    result = order(client, text, reviewed)
    assert result['state'] == 'CANCELLED'
    assert result['basket'] == []
    assert 'No order was placed' in result['reply_text']

def test_explicit_confirmation_does_not_call_local_model(client, monkeypatch):
    from api import main
    reviewed = order(client, 'One coffee')
    monkeypatch.setenv('USE_MOCK_AI', 'false')
    async def unexpected_model_call(*args, **kwargs):
        raise AssertionError('Explicit confirmation should not call Ollama')
    monkeypatch.setattr(main, 'real_interpret', unexpected_model_call)
    assert order(client, 'confirm order', reviewed)['state'] == 'CONFIRMED'

def test_cloud_failures_are_redacted(client, monkeypatch):
    from api import voice
    monkeypatch.setenv('USE_CLOUD_VOICE', 'true')
    monkeypatch.setenv('DEEPGRAM_API_KEY', 'test-secret')
    monkeypatch.setenv('ELEVENLABS_API_KEY', 'test-secret')
    async def fail(*args, **kwargs): raise httpx.ConnectError('test-secret provider detail')
    monkeypatch.setattr(voice.httpx.AsyncClient, 'post', fail)
    assert client.post('/voice/speak', json={'text': 'Hello'}).status_code == 503
    response = client.post('/voice/transcribe', content=b'fake', headers={'Content-Type': 'audio/webm'})
    assert response.status_code == 503
    assert 'test-secret' not in response.text
    assert client.post('/voice/transcribe', content=b'a' * (4 * 1024 * 1024 + 1), headers={'Content-Type': 'audio/webm'}).status_code == 413

def test_voice_transcription_uses_local_model_by_default(client, monkeypatch):
    from api import voice
    monkeypatch.setenv('USE_CLOUD_VOICE', 'false')
    monkeypatch.delenv('DEEPGRAM_API_KEY', raising=False)
    monkeypatch.setattr(voice.importlib.util, 'find_spec', lambda name: object())
    async def transcribe_in_memory(function, audio):
        assert function is voice._transcribe_locally
        assert audio == b'local audio'
        return 'two coffees and one croissant'
    monkeypatch.setattr(voice, 'run_in_threadpool', transcribe_in_memory)
    response = client.post('/voice/transcribe', content=b'local audio', headers={'Content-Type': 'audio/wav'})
    assert response.status_code == 200
    assert response.json() == {'text': 'two coffees and one croissant'}

def test_real_local_voice_transcription_with_synthetic_audio(client, monkeypatch):
    import io
    import struct
    import wave
    monkeypatch.setenv('USE_CLOUD_VOICE', 'false')
    monkeypatch.delenv('DEEPGRAM_API_KEY', raising=False)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(struct.pack('<h', 0) * 16000)
    wav_bytes = buf.getvalue()
    response = client.post('/voice/transcribe', content=wav_bytes, headers={'Content-Type': 'audio/wav'})
    assert response.status_code == 200
    assert response.json() == {'text': ''}

def test_cloud_deepgram_and_elevenlabs_routing(client, monkeypatch):
    from api import voice
    monkeypatch.setenv('USE_CLOUD_VOICE', 'true')
    monkeypatch.setenv('DEEPGRAM_API_KEY', 'valid-dg-key')
    monkeypatch.setenv('ELEVENLABS_API_KEY', 'valid-el-key')
    config = client.get('/voice/config').json()
    assert config['stt'] is True
    assert config['tts'] is True
    assert config['local_stt'] is False

    class FakeResponse:
        def __init__(self, content, status=200):
            self.content = content
            self.status_code = status
        def raise_for_status(self): pass
        def json(self): return {'results': {'channels': [{'alternatives': [{'transcript': 'one coffee please'}]}]}}

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            if 'deepgram' in url:
                return FakeResponse(b'')
            if 'elevenlabs' in url:
                return FakeResponse(b'audio-bytes-elevenlabs')
            raise AssertionError(f'Unexpected url {url}')

    monkeypatch.setattr(voice.httpx, 'AsyncClient', lambda **kw: FakeClient())
    stt_res = client.post('/voice/transcribe', content=b'fake-audio', headers={'Content-Type': 'audio/wav'})
    assert stt_res.status_code == 200
    assert stt_res.json() == {'text': 'one coffee please'}

    tts_res = client.post('/voice/speak', json={'text': 'Hello'})
    assert tts_res.status_code == 200
    assert tts_res.content == b'audio-bytes-elevenlabs'

def test_qwen_reasoning_inquiry_and_messy_order(client, monkeypatch):
    from api import interpreter
    inquiry_payload = {
        'action': 'inquiry',
        'items': [],
        'unmatched_items': [],
        'suggestion_or_question': 'Our Coffee and Moroccan Mint Tea are very popular! What flavor profile do you prefer?',
    }
    class FakeInquiryClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs):
            class R:
                def raise_for_status(self): pass
                def json(self): return {'message': {'content': json.dumps(inquiry_payload)}}
            return R()

    monkeypatch.setenv('USE_MOCK_AI', 'false')
    monkeypatch.setattr(interpreter.httpx, 'AsyncClient', lambda **kw: FakeInquiryClient())
    res_inquiry = client.post('/interpret', json={'text': 'I am not sure what to drink, what do you recommend?', 'restaurant_id': 'demo'})
    assert res_inquiry.status_code == 200
    inquiry_data = res_inquiry.json()
    assert inquiry_data['state'] == 'CLARIFY'
    assert 'misunderstood' in inquiry_data['reply_text']  # Model prose is never spoken directly.

    order_payload = {
        'action': 'order',
        'items': [
            {'product_id': 'coffee', 'quantity': 2, 'modifier_ids': ['large', 'no_sugar']},
            {'product_id': 'croissant', 'quantity': 1, 'modifier_ids': []}
        ],
        'unmatched_items': ['muffin'],
        'suggestion_or_question': None
    }
    class FakeOrderClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs):
            class R:
                def raise_for_status(self): pass
                def json(self): return {'message': {'content': json.dumps(order_payload)}}
            return R()

    monkeypatch.setattr(interpreter.httpx, 'AsyncClient', lambda **kw: FakeOrderClient())
    res_order = client.post('/interpret', json={'text': 'two large coffees without sugar and a croissant and a muffin', 'restaurant_id': 'demo'})
    assert res_order.status_code == 200
    order_data = res_order.json()
    assert order_data['state'] == 'REVIEW'
    assert len(order_data['basket']) == 2
    assert order_data['total_mad'] == 46
    assert 'muffin' in order_data['reply_text']



@pytest.mark.parametrize('payload', ['not json', '{"intent":"add","product_id":"invented"}',
    '{"intent":"add","product_id":"coffee","quantity":true}', '{"intent":"confirm","price":1}'])
def test_malformed_model_outputs_fail_closed(monkeypatch, payload):
    from api import interpreter
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return {'message': {'content': payload}}
    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): return FakeResponse()
    monkeypatch.setattr(interpreter.httpx, 'AsyncClient', lambda **kw: FakeClient())
    result = asyncio.run(interpret('one coffee', DEMO_MENU, [], 'REQUEST', None))
    assert result['intent'] == 'unknown'
