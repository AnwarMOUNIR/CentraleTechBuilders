import asyncio
import json
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.catalog import CATALOG, DEMO_MENU
from api.logic import next_step
from api.recommendation import spoken_order_lines
from api.storage import search_catalog, history, conversation_context

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv('ORDER_DB_PATH', str(tmp_path / 'test.db'))
    monkeypatch.setenv('USE_MOCK_AI', 'true')

def coffee():
    return {'product_id':'coffee','quantity':1,'modifier_ids':[],'line_total_mad':0.01}

def test_invalid_basket_preserves_valid_items_and_blocks_confirmation():
    result = next_step({'intent':'confirm'}, [coffee(),{**coffee(),'product_id':'missing'}], 'REVIEW', DEMO_MENU)
    assert result['state'] == 'CLARIFY'
    assert result['total_mad'] == 12
    assert len(result['basket']) == 1

def test_cross_restaurant_summary():
    r,p = next((r,p) for r in CATALOG for p in r['menu'] if 'pastilla' in p['id'])
    basket = [coffee(), {**coffee(),'product_id':p['id']}]
    result = next_step({'intent':'confirm'}, basket, 'REVIEW', r['menu'])
    spoken = spoken_order_lines({'restaurant':r,**result,'unmatched_items':[]})
    assert 'coffee' in spoken and 'pastilla' in spoken
    assert 'Combined food subtotal' in spoken

def test_model_cannot_confirm_ambiguous_approval(monkeypatch):
    monkeypatch.setenv('USE_MOCK_AI','false')
    monkeypatch.setattr('api.main.real_interpret', AsyncMock(return_value={'intent':'confirm'}))
    c=TestClient(app)
    result=c.post('/interpret',json={'text':'I like it but am still deciding','basket':[coffee()],'state':'REVIEW'}).json()
    assert result['state']=='REVIEW'
    assert result['total_mad']==12
    assert c.post('/interpret',json={**result,'text':'confirm order'}).json()['state']=='CONFIRMED'

def test_sql_search_plural_alias_and_injection():
    found=search_catalog('two coffees and bastilla',CATALOG)
    names=[p['name'].lower() for r in found for p in r['menu']]
    assert 'coffee' in names and 'fish pastilla' in names
    search_catalog("'; DROP TABLE items_available; --",CATALOG)
    assert search_catalog('croissant',CATALOG)

def test_logs_are_redacted_and_sessions_isolated():
    c=TestClient(app)
    c.post('/conversation-events',json={'conversation_id':'one','speaker':'user','text':'Call +212612345678'})
    assert '212612345678' not in json.dumps(c.get('/conversations/one').json())
    assert c.get('/conversations/two').json()==[]
    result=c.post('/interpret',json={'conversation_id':'two','text':'one coffee'}).json()
    assert result['conversation_id']=='two'
    assert [e['speaker'] for e in history('two')]==['user','assistant']
    assert 'basket' in json.loads(history('two')[-1]['details'])

def test_context_includes_previous_turns(monkeypatch):
    c=TestClient(app)
    c.post('/interpret',json={'conversation_id':'memory','text':'one coffee'})
    async def fake(*args):
        assert conversation_context.get()[0]['content']=='one coffee'
        return {'intent':'repeat'}
    monkeypatch.setenv('USE_MOCK_AI','false')
    monkeypatch.setattr('api.main.real_interpret',fake)
    assert c.post('/interpret',json={'conversation_id':'memory','text':'repeat'}).status_code==200
    assert conversation_context.get()==[]
