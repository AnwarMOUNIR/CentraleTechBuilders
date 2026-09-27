import pytest
from fastapi.testclient import TestClient
from api.main import app
from api import order_agent as agent

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('ORDER_DB_PATH',str(tmp_path/'agent.db'))
    monkeypatch.setenv('USE_MOCK_AI','false')
    monkeypatch.setenv('USE_VERIFIED_AI','true')
    return TestClient(app)

def mock_pipeline(monkeypatch,decision,approved=True):
    async def ask(schema,system,data):
        if schema==agent.SearchPlan: return schema(queries=['coffee'],browse=False)
        if schema==agent.Decision: return schema(**decision)
        return schema(**{k:([] if k=='problems' else approved) for k in schema.model_fields})
    monkeypatch.setattr(agent,'ask',ask)

def test_rejected_verification_cannot_mutate(client,monkeypatch):
    mock_pipeline(monkeypatch,{'action':'apply','items':[{'product_id':'coffee','quantity':3,'modifier_ids':[]}],'reply':'Added.'},False)
    result=client.post('/interpret',json={'text':'do something'}).json()
    assert result['basket']==[] and result['error']

def test_unknown_product_cannot_mutate(client,monkeypatch):
    mock_pipeline(monkeypatch,{'action':'apply','items':[{'product_id':'fake','quantity':1,'modifier_ids':[]}],'reply':'Added.'})
    assert client.post('/interpret',json={'text':'coffee'}).json()['basket']==[]

def test_internal_prose_blocked_even_if_verifier_approves(client,monkeypatch):
    mock_pipeline(monkeypatch,{'action':'reply','items':[],'reply':'The customer is asking about coffee. I should clarify.'})
    result=client.post('/interpret',json={'text':'explain'}).json()
    assert 'The customer' not in result['reply_text']

def test_confirmation_still_requires_explicit_user_consent(client,monkeypatch):
    mock_pipeline(monkeypatch,{'action':'confirm','items':[],'reply':'Confirmed.'})
    result=client.post('/interpret',json={'text':'perfect','state':'REVIEW','basket':[{'product_id':'coffee','quantity':1,'modifier_ids':[],'line_total_mad':12}]}).json()
    assert result['state']=='REVIEW'

def test_live_recommendation_does_not_bypass_agent(client):
    assert client.post('/recommend',json={'text':'coffee and hot drink'}).json()['matched'] is False
