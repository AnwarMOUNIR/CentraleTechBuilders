"""Bounded offline English commands; no network and no invented products."""
import re

UNKNOWN = dict(intent='unknown', product_id=None, quantity=None, modifier_ids=[], missing_field=None)
CONFIRM_PHRASES = {
    'confirm', 'confirm order', 'confirm my order', 'confirm the order', 'confirm this order',
    'yes confirm', 'yes confirm order', 'yes please confirm', 'please confirm', 'please confirm order',
    'please confirm the order', 'i confirm', 'i confirm my order', 'i confirm the order',
    'place order', 'place my order', 'place the order', 'please place order', 'please place the order',
}

def normalize(text):
    return re.sub(r'[^a-z0-9\s]', '', text.casefold()).strip()

def explicit_confirmation(text):
    s = normalize(text)
    if s in CONFIRM_PHRASES:
        return True
    if re.search(r'\b(dont|do not|never|no|not)\b', s):
        return False
    cleaned = re.sub(r'^(?:please\s+|yes\s+please\s+|yes\s+|i\s+)', '', s).strip()
    cleaned = re.sub(r'\b(?:the|this|my)\s+order\b', 'order', cleaned)
    return cleaned in {'confirm', 'confirm order', 'place order'}

async def interpret(text, menu, basket, state, pending):
    s = normalize(text)
    base = {**UNKNOWN, 'modifier_ids': []}
    if explicit_confirmation(text):
        return {**base, 'intent': 'confirm'}
    if s in {'cancel', 'cancel order', 'cancel my order', 'never mind'}:
        return {**base, 'intent': 'cancel'}
    if s in {'repeat', 'repeat that', 'say that again', 'what is my total'}:
        return {**base, 'intent': 'repeat'}
    if re.search(r'\b(dont|not|never|no)\s+confirm', s) or 'confirm' in s:
        return base
    words = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'a': 1, 'an': 1, 'zero': 0}
    quantity = next((int(w) if w.isdigit() else words[w] for w in s.split() if w.isdigit() or w in words), None)
    modifiers = []
    aliases = {'no_sugar': ['no sugar', 'without sugar'], 'no_ice': ['no ice', 'without ice'],
               'no_tomato': ['no tomato', 'without tomato'], 'no_honey': ['no honey', 'without honey']}
    for mid in {m['id'] for p in menu for m in p.get('modifiers', [])}:
        terms = aliases.get(mid, [mid.replace('_', ' ')])
        if any(re.search(r'\b' + re.escape(t) + r'\b', s) for t in terms):
            modifiers.append(mid)
    modifiers.sort(key=lambda x: (x not in {'small', 'large'}, x))
    matching = []
    for p in menu:
        terms = [p['name'].casefold(), p['id'].replace('_', ' ')] + p.get('aliases', [])
        if p['id'] == 'coffee': terms += ['coffees']
        if any(re.search(r'\b' + re.escape(normalize(t)) + r'\b', s) for t in terms): matching.append(p)
    if len(matching) > 1: return base
    product_id = matching[0]['id'] if matching else None
    changing = any(term in s for term in ('change', 'make that', 'instead')) or bool(pending and pending.get('missing_field') == 'change')
    if changing:
        return {**base, 'intent': 'change', 'product_id': product_id, 'quantity': quantity, 'modifier_ids': modifiers}
    if pending and (quantity is not None or modifiers):
        return {**base, 'intent': 'add', 'quantity': quantity, 'modifier_ids': modifiers}
    if product_id:
        return {**base, 'intent': 'add', 'product_id': product_id, 'quantity': quantity,
                'modifier_ids': modifiers}
    return base
