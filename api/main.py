"""Local simulated ordering API with bounded server-side speech services."""
import asyncio
import os
import re
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
from api.catalog import CATALOG, get_restaurant
from api.interpreter import interpret as real_interpret
from api.interpreter_mock import interpret as mock_interpret, explicit_confirmation, normalize
from api.logic import next_step, summary
from api.privacy import redact
from api.recommendation import (
    recommend_order as recommend_from_catalog,
    recommend_with_ollama,
    spoken_recommendation,
    spoken_order_lines,
)
from api.voice import router as voice_router
from api.storage import log_event, history, conversations, conversation_context
from uuid import uuid4
from api.dialogue import route, constrain

State = Literal['REQUEST', 'CLARIFY', 'REVIEW', 'CONFIRMED', 'CANCELLED']
MENU = CATALOG[0]['menu']

class BasketLine(BaseModel):
    product_id: str
    quantity: int = Field(ge=1, le=99, strict=True)
    modifier_ids: list[str] = Field(default_factory=list, max_length=20)
    line_total_mad: float = Field(default=0, ge=0, allow_inf_nan=False)

class PendingItem(BaseModel):
    proposal_items: list[BasketLine] = Field(default_factory=list, max_length=20)
    product_id: str | None = None
    quantity: int | None = None
    modifier_ids: list[str] = Field(default_factory=list, max_length=20)
    missing_field: str | None = None

class InterpretRequest(BaseModel):
    conversation_id: str | None = Field(default=None, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')
    text: str = Field(min_length=1, max_length=500)
    basket: list[BasketLine] = Field(default_factory=list, max_length=20)
    state: State = 'REQUEST'
    pending: PendingItem | None = None
    restaurant_id: str = 'demo'

class RecommendationRequest(BaseModel):
    conversation_id: str | None = Field(default=None, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')
    text: str = Field(min_length=1, max_length=500)

class InterpretResponse(BaseModel):
    conversation_id: str | None = None
    state: State
    reply_text: str
    basket: list[BasketLine]
    total_mad: float
    pending: PendingItem | None = None
    question: str | None = None
    error: str | None = None
    mode: str = 'mock'
    restaurant_id: str = 'demo'

app = FastAPI(title='ClearOrder — simulated ordering', version='1.0.0')
app.include_router(voice_router)

def _use_mock():
    return os.getenv('USE_MOCK_AI', 'false').lower().strip() not in {'false', '0', 'no'}

@app.get('/health')
async def health():
    return {'status': 'ok', 'mode': 'mock' if _use_mock() else 'ollama',
            'model': os.getenv('OLLAMA_MODEL', 'qwen3:4b')}

@app.get('/catalog')
async def catalog():
    return CATALOG

async def recommend(request: RecommendationRequest):
    if not _use_mock() and os.getenv('USE_VERIFIED_AI','false').lower()=='true':
        return {'matched':False}  # One model-led dialogue path, not a competing keyword recommender.
    text = redact(request.text)
    if route(text, [], None, CATALOG[0]) is not None: return {'matched':False}
    matched_selection = recommend_from_catalog(text, CATALOG, across_restaurants=True)
    model_selection = None if matched_selection or _use_mock() else await recommend_with_ollama(text, CATALOG)
    selection = model_selection or matched_selection
    selection_source = 'ollama' if model_selection else 'catalog_match'
    if model_selection and matched_selection:
        model_score = (len(model_selection['basket']), -model_selection['total_mad'])
        matched_score = (len(matched_selection['basket']), -matched_selection['total_mad'])
        if matched_score > model_score:
            selection = matched_selection
            selection_source = 'catalog_match'
    if selection is None:
        return {'matched': False}
    restaurant = selection['restaurant']
    basket = selection['basket']
    reply = spoken_recommendation(selection)
    return {
        'matched': True,
        'selection_source': selection_source,
        'restaurant_id': restaurant['id'],
        'state': 'REVIEW',
        'reply_text': reply,
        'basket': basket,
        'total_mad': selection['total_mad'],
        'pending': None,
        'question': None,
        'error': None,
        'unmatched_items': selection['unmatched_items'],
    }

def is_prose_safe(text: str | None) -> bool:
    if not text or not isinstance(text, str):
        return False
    prose_patterns = [
        r'<\/?think',
        r'\b(?:the\s+)?(?:customer|user)\s+(?:is|wants|asked|said)\b',
        r'\bi\s+(?:should|must|need to|will)\s+(?:respond|clarify|reason|answer)\b',
        r'\bchain[\s_]of[\s_]thought\b',
        r'\bsystem\s+prompt\b',
        r'\blive\s+availability\b',
        r'\breal\s+order\b',
        r'\bplace\s+your\s+real\s+order\b',
    ]
    for pattern in prose_patterns:
        if re.search(pattern, text, re.I):
            return False
    return True

async def interpret_order(request: InterpretRequest):
    restaurant = get_restaurant(request.restaurant_id)
    if not restaurant: raise HTTPException(400, 'Unknown restaurant')
    menu = restaurant['menu']
    text = redact(request.text)
    basket = [b.model_dump() for b in request.basket]
    pending = request.pending.model_dump() if request.pending else None
    state = request.state
    if not _use_mock() and os.getenv('USE_VERIFIED_AI','false').lower()=='true':
        from api.order_agent import respond
        try:
            return await asyncio.wait_for(respond(text,basket,state,pending,restaurant['id']),timeout=75)
        except (asyncio.TimeoutError,ValueError,KeyError):
            return {'state':state,'basket':basket,'total_mad':sum(l['line_total_mad'] for l in basket),
                    'pending':pending,'restaurant_id':restaurant['id'],'mode':'ollama-verified',
                    'reply_text':'I could not verify your request in time. Your basket is unchanged; please try again.',
                    'error':'Verification unavailable'}
    terminal_action = route(text,basket,pending,restaurant) if state in {'CONFIRMED','CANCELLED'} else None
    if state in {'CONFIRMED', 'CANCELLED'} and (terminal_action or {}).get('intent') not in {'repeat','inquiry'}:
        basket, pending, state = [], None, 'REQUEST'
    mode = 'mock' if _use_mock() else 'ollama'
    grounded = route(text,basket,pending,restaurant)
    if normalize(text) in {'help', 'read menu'}:
        result = next_step({'intent': 'repeat'}, basket, state, menu, pending)
        result['reply_text'] = restaurant['name'] + '. ' + '; '.join(
            f"{p['name']}, {p['base_price_mad']:g} dirhams" for p in menu)
        result['reply_text'] += '. You can describe several items at once. Say confirm order, or say no to discard the proposal.'
    else:
        no_confirmation = {
            'no', 'no cancel', 'no thanks', 'no thank you', 'dont confirm', 'do not confirm',
            'not confirm', 'not now', 'dont place it', 'do not place it', 'reject order',
        }
        is_negative_confirmation = normalize(text) in no_confirmation or bool(
            re.match(r'^(?:no\s+)?(?:dont|do not|not)\s+(?:confirm|place|order)\b', normalize(text))
        )
        if grounded is not None:
            parsed = grounded
        elif explicit_confirmation(text):
            parsed = {'intent': 'confirm'}
        elif state == 'REVIEW' and is_negative_confirmation:
            parsed = {'intent': 'cancel'}
        else:
            s_norm = normalize(text)
            direct_add = None
            is_addition_phrase = bool(
                re.search(r'\b(add|also|and|plus|another|one more|get me|give me|bring me)\b', s_norm) or
                re.match(r'^(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+', s_norm)
            )
            is_change_phrase = bool(re.search(r'\b(change|make that|instead|actually|remove|delete|replace|without|no sugar|extra)\b', s_norm))
            if state == 'REVIEW' and not pending and is_addition_phrase and not is_change_phrase:
                matched_cand = recommend_from_catalog(text, [restaurant])
                if not (matched_cand and matched_cand['basket'] and not matched_cand.get('unmatched_items')):
                    matched_cand = recommend_from_catalog(text, CATALOG, across_restaurants=True)
                if matched_cand and matched_cand['basket'] and not matched_cand.get('unmatched_items'):
                    direct_add = {
                        'intent': 'add',
                        'restaurant_id': matched_cand['restaurant']['id'],
                        'items': matched_cand['basket'],
                        'product_id': matched_cand['basket'][0]['product_id'],
                        'quantity': matched_cand['basket'][0]['quantity'],
                        'modifier_ids': matched_cand['basket'][0]['modifier_ids'],
                        'unmatched_items': [],
                        'missing_field': None,
                    }
            if direct_add is not None:
                parsed = direct_add
            else:
                try:
                    parsed = await asyncio.wait_for((mock_interpret if _use_mock() else real_interpret)(
                        text, menu, basket, state, pending), timeout=30)
                    if parsed.get('intent') == 'inquiry':
                        # Model prose is not an approved spoken response. Only application
                        # templates may make claims or ask actionable questions.
                        parsed = {'intent':'inquiry', 'suggestion_or_question':
                            'I may have misunderstood. Please name a dish, say hot drink or cold drink, or ask for the menu. Your basket is unchanged.'}
                except (Exception, asyncio.TimeoutError):
                    parsed = {'intent': 'unknown'}
        parsed = constrain(parsed,text) if parsed.get('intent') not in {'accept_offer'} else parsed
        if parsed.get('intent') == 'confirm' and not explicit_confirmation(text):
            parsed = {'intent': 'inquiry', 'suggestion_or_question': 'Your order is still a proposal. Say confirm order when you are ready, or tell me what to change.'}
        # If Qwen matched a different restaurant in the catalog:
        if parsed.get('restaurant_id') and parsed['restaurant_id'] != restaurant['id']:
            new_r = get_restaurant(parsed['restaurant_id'])
            if new_r:
                restaurant = new_r
                menu = new_r['menu']

        result = next_step(parsed, basket, state, menu, pending)
        if result['state'] == 'CONFIRMED':
            result['reply_text'] = 'Simulated order confirmed. ' + spoken_order_lines({
                'restaurant': restaurant,
                'basket': result['basket'],
                'total_mad': result['total_mad'],
                'unmatched_items': [],
            }) + ' No payment or delivery will take place.'
    result['restaurant_id'] = restaurant['id']
    result['mode'] = mode
    return result

async def recorded(request, handler):
    cid = request.conversation_id or uuid4().hex
    previous = history(cid, 100)
    token = conversation_context.set([{'role':r['speaker'], 'content':r['text']} for r in previous
                                      if r['speaker'] in {'user', 'assistant'}][-6:])
    try:
        result = await handler(request)
        result['conversation_id'] = cid
        if result.get('matched') is not False:
            log_event(cid, 'user', request.text)
            log_event(cid, 'assistant', result.get('reply_text', ''),
                      {k:result[k] for k in ('state','basket','total_mad','error','agent_trace') if k in result})
        return result
    except Exception as exc:
        log_event(cid, 'error', type(exc).__name__)
        raise
    finally:
        conversation_context.reset(token)

@app.post('/interpret', response_model=InterpretResponse)
async def interpret_recorded(request: InterpretRequest):
    return await recorded(request, interpret_order)

@app.post('/recommend')
async def recommend_recorded(request: RecommendationRequest):
    return await recorded(request, recommend)

@app.get('/conversations')
async def list_conversations():
    return conversations()

@app.get('/conversations/{conversation_id}')
async def read_conversation(conversation_id: str):
    return history(conversation_id, 500)

class DebugEvent(BaseModel):
    conversation_id: str = Field(max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')
    speaker: Literal['user', 'assistant', 'error', 'playback']
    text: str = Field(max_length=4000)

@app.post('/conversation-events')
async def record_browser_event(request: DebugEvent):
    log_event(request.conversation_id, request.speaker, request.text)
    return {'ok': True}

# A built frontend can be served by this one local process.
if (ROOT / 'dist').is_dir():
    app.mount('/', StaticFiles(directory=ROOT / 'dist', html=True), name='web')
