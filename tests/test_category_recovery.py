import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from api.main import app
from api.catalog import get_product_and_restaurant

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('ORDER_DB_PATH',str(tmp_path/'category.db'))
    monkeypatch.setenv('USE_MOCK_AI','true')
    return TestClient(app)

def turn(c,text,previous=None):
    r=c.post('/interpret',json={**(previous or {}),'text':text})
    assert r.status_code==200,r.text
    return r.json()

@pytest.mark.parametrize('text',[
 'I would like one hot drink, one cold drink, and I would like something with fish.',
 'One warm beverage and one chilled drink and fish pastilla',
 'a hot drink and a cold drink and fish',
])
def test_complete_category_proposal(client,text):
    assert client.post('/recommend',json={'text':text}).json()['matched'] is False
    proposal=turn(client,text)
    assert proposal['basket']==[]
    assert len(proposal['pending']['proposal_items'])==3
    assert turn(client,'confirm order',proposal)['state']!='CONFIRMED'
    added=turn(client,'yes',proposal)
    assert len(added['basket'])==3 and added['pending'] is None
    names=' '.join(get_product_and_restaurant(l['product_id'])[1]['name'].lower() for l in added['basket'])
    assert 'coffee' in names and 'juice' in names and 'fish' in names
    again=turn(client,'yes',added)
    assert again['basket']==added['basket']
    assert turn(client,'confirm order',added)['state']=='CONFIRMED'

@pytest.mark.parametrize('text',['hot drink','cold drink','warm beverage','chilled beverage'])
def test_single_category_and_decline(client,text):
    before=turn(client,'one croissant')
    proposal=turn(client,text,before)
    assert proposal['basket']==before['basket']
    assert len(proposal['pending']['proposal_items'])==1
    declined=turn(client,'no',proposal)
    assert declined['basket']==before['basket'] and declined['pending'] is None

@pytest.mark.parametrize('text', ["Why didn't you include the heart rate?",'Heartbreak.','heart break'])
def test_recorded_mishearing_asks_not_guesses(client,text):
    proposal=turn(client,'one hot drink and one cold drink',{'conversation_id':'recovery'})
    result=turn(client,text,proposal)
    assert 'misheard hot drink' in result['reply_text']
    assert result['basket']==proposal['basket']
    assert result['pending']==proposal['pending']
    assert len(turn(client,'yes',result)['basket'])==2

@pytest.mark.parametrize('prose',[
 'The customer is asking about heart rate. I should clarify.',
 '<think>I need to reason about this</think> Please wait.',
 'I will respond in a friendly conversational way.',
 'I can check live availability and place your real order.',
])
def test_model_prose_not_spoken(client,monkeypatch,prose):
    monkeypatch.setenv('USE_MOCK_AI','false')
    monkeypatch.setattr('api.main.real_interpret',AsyncMock(return_value={'intent':'inquiry','suggestion_or_question':prose}))
    result=turn(client,'Explain that differently please')
    assert prose not in result['reply_text']
    assert 'misunderstood' in result['reply_text']

@pytest.mark.parametrize('text',['zero hot drinks','-2 cold drinks','100 warm beverages','1.5 hot drinks'])
def test_invalid_category_quantity(client,text):
    result=turn(client,text)
    assert result['basket']==[] and result['pending'] is None

def test_unknown_part_no_partial_add(client):
    result=turn(client,'one hot drink and sushi')
    assert result['basket']==[] and result['pending'] is None
    assert 'could not match every part' in result['reply_text']

def test_repeat_proposal_and_unclear_reply_preserve_every_item(client):
    proposal=turn(client,'two hot drinks and one cold drink and fish')
    repeat=turn(client,'repeat',proposal)
    assert 'not yet added' in repeat['reply_text']
    assert repeat['pending']==proposal['pending']
    unclear=turn(client,'something else maybe',repeat)
    assert unclear['pending']==proposal['pending'] and unclear['basket']==[]
    clarified=turn(client,'hot drink',unclear)
    assert clarified['pending']==proposal['pending']
    added=turn(client,'yes',unclear)
    assert len(added['basket'])==3
    assert sum(l['quantity'] for l in added['basket'])==4
