"""Match a spoken order against sampled menus and rank suitable restaurants."""

from __future__ import annotations

import re
import unicodedata
import json
import logging
import os

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from api.logic import price_line, summary

logger = logging.getLogger(__name__)


class SelectedItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    product_id: str
    quantity: int = Field(ge=1, le=99)
    modifier_ids: list[str] = Field(default_factory=list, max_length=20)


class ModelSelection(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    restaurant_id: str
    items: list[SelectedItem] = Field(min_length=1, max_length=20)
    unmatched_items: list[str] = Field(default_factory=list, max_length=20)

GENERIC_TERMS = {
    'burger', 'coffee', 'croissant', 'fish', 'juice', 'meal', 'pasta', 'pastilla',
    'pizza', 'pitta', 'salad', 'sandwich', 'steak', 'taco', 'tea', 'water',
    'briouates', 'carpaccio', 'parmigiana', 'sticks', 'mezze',
}
QUANTITIES = {
    'a': 1, 'an': 1, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
    'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
}
MODIFIERS = {
    'extra sugar': 'extra_sugar', 'without sugar': 'no_sugar', 'no sugar': 'no_sugar',
    'extra mint': 'extra_mint', 'extra cheese': 'extra_cheese', 'no tomato': 'no_tomato',
    'no honey': 'no_honey', 'no ice': 'no_ice', 'sparkling': 'sparkling',
    'large': 'large', 'small': 'small', 'spicy': 'spicy',
}
QUANTITY_WORDS = {
    1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five',
    6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten',
}


def _pluralize_product(name: str) -> str:
    words = name.split()
    last = words[-1]
    lowered = last.casefold()
    if lowered.endswith('s'):
        return name
    if lowered.endswith('y') and len(last) > 1 and lowered[-2] not in 'aeiou':
        plural = last[:-1] + 'ies'
    elif lowered.endswith(('ch', 'sh', 'x')):
        plural = last + 'es'
    else:
        plural = last + 's'
    return ' '.join(words[:-1] + [plural])


def spoken_order_lines(selection: dict) -> str:
    """Format item names, options, and prices as short, natural speech."""
    restaurant = selection['restaurant']
    from api.catalog import get_product_and_restaurant
    groups = {}
    for line in selection['basket']:
        pair = get_product_and_restaurant(line['product_id'])
        owner = pair[0] if pair else restaurant
        groups.setdefault(owner['id'], (owner, []))[1].append(line)
    if len(groups) > 1 or (groups and restaurant['id'] not in groups):
        return ' '.join(spoken_order_lines({'restaurant': owner, 'basket': lines,
            'total_mad': round(sum(l['line_total_mad'] for l in lines), 2), 'unmatched_items': []})
            for owner, lines in groups.values()) + f" Combined food subtotal: {selection['total_mad']:g} dirhams."
    products = {product['id']: product for product in restaurant['menu']}
    size_words = {'small', 'large', 'spicy'}
    modifier_phrases = {
        'no_sugar': 'without sugar', 'no_ice': 'without ice',
        'no_tomato': 'without tomato', 'no_honey': 'without honey',
        'extra_mint': 'with extra mint', 'extra_cheese': 'with extra cheese',
    }
    lines = []
    for line in selection['basket']:
        product = products[line['product_id']]
        name = product['name']
        quantity = line['quantity']
        if quantity > 1:
            name = _pluralize_product(name)
        name = name[:1].lower() + name[1:]
        modifiers = line['modifier_ids']
        prefixes = [modifier for modifier in modifiers if modifier in size_words]
        phrase = ' '.join([*prefixes, name])
        suffixes = [modifier_phrases.get(
            modifier,
            next((option['label'].casefold() for option in product.get('modifiers', [])
                  if option['id'] == modifier), modifier.replace('_', ' ')),
        ) for modifier in modifiers if modifier not in size_words]
        if suffixes:
            phrase += ' ' + ' and '.join(suffixes)
        quantity_text = QUANTITY_WORDS.get(quantity, str(quantity))
        lines.append(f'{quantity_text} {phrase}, {line["line_total_mad"]:g} dirhams')

    sentence = f"At {restaurant['name']}: " + '; '.join(lines)
    sentence += f". The total is {selection['total_mad']:g} dirhams."
    included_words = {w.lower() for line in selection['basket']
                      for w in products[line['product_id']]['name'].lower().split()}
    real_unmatched = [
        item for item in selection['unmatched_items']
        if item.lower() not in included_words
    ]
    if real_unmatched:
        sentence += ' I could not include ' + ', '.join(real_unmatched) + '.'
    return sentence


def spoken_recommendation(selection: dict) -> str:
    """Format a proposed basket with a clear, unhurried confirmation prompt."""
    return 'I found a good match. ' + spoken_order_lines(selection) + ' This is only a proposal. Say confirm order, or say no, cancel.'


PHONETIC_REPLACEMENTS = {
    'bastilla': 'pastilla',
    'pastila': 'pastilla',
    'pastela': 'pastilla',
    'bisteya': 'pastilla',
    'briouat': 'briouates',
    'briwat': 'briouates',
}


def _normalize(value: str) -> str:
    ascii_text = unicodedata.normalize('NFKD', value.casefold()).encode('ascii', 'ignore').decode()
    words = re.findall(r'[a-z0-9]+', ascii_text)
    normalized_words = [PHONETIC_REPLACEMENTS.get(w, w) for w in words]
    return ' '.join(normalized_words)


def _plural_forms(alias: str) -> set[str]:
    words = alias.split()
    last = words[-1]
    if last.endswith('y') and len(last) > 1 and last[-2] not in 'aeiou':
        plural = last[:-1] + 'ies'
    elif last.endswith(('s', 'x', 'ch', 'sh')):
        plural = last + 'es'
    else:
        plural = last + 's'
    return {alias, ' '.join(words[:-1] + [plural])}


def _product_aliases(name: str) -> set[str]:
    words = _normalize(name).split()
    aliases = {' '.join(words)}
    aliases.update(word for word in words if word in GENERIC_TERMS)
    return aliases


def _find_mentions(text: str, catalog: list[dict]) -> list[dict]:
    aliases: dict[str, list[tuple[dict, dict]]] = {}
    for restaurant in catalog:
        for product in restaurant['menu']:
            for alias in _product_aliases(product['name']):
                aliases.setdefault(alias, []).append((restaurant, product))

    matches = []
    for alias, products in aliases.items():
        for form in _plural_forms(alias):
            pattern = r'(?<![a-z0-9])' + re.escape(form).replace(r'\ ', r'\s+') + r'(?![a-z0-9])'
            for found in re.finditer(pattern, text):
                matches.append({'start': found.start(), 'end': found.end(), 'alias': alias, 'products': products})

    selected = []
    for match in sorted(matches, key=lambda item: (-(item['end'] - item['start']), item['start'], item['alias'])):
        if any(match['start'] < item['end'] and match['end'] > item['start'] for item in selected):
            continue
        selected.append(match)

    selected.sort(key=lambda item: item['start'])
    for mention in selected:
        preceding_words = re.findall(r'[a-z]+|\d+', text[max(0, mention['start'] - 40):mention['start']])
        mention['quantity'] = 1
        for distance, word in enumerate(reversed(preceding_words[-4:])):
            quantity = int(word) if word.isdigit() else QUANTITIES.get(word)
            if quantity is not None:
                if distance <= 3 and 1 <= quantity <= 99:
                    mention['quantity'] = quantity
                break
        mention['modifier_ids'] = []
    return selected


def _attach_modifiers(text: str, mentions: list[dict]) -> None:
    modifier_matches = []
    for phrase, modifier_id in MODIFIERS.items():
        pattern = r'(?<![a-z0-9])' + re.escape(phrase) + r'(?![a-z0-9])'
        modifier_matches.extend((found.start(), found.end(), modifier_id) for found in re.finditer(pattern, text))

    modifier_matches.sort()
    for modifier_start, modifier_end, modifier_id in modifier_matches:
        candidates = []
        for index, mention in enumerate(mentions):
            if modifier_end <= mention['start']:
                between = text[modifier_end:mention['start']]
                distance = mention['start'] - modifier_end
            elif modifier_start >= mention['end']:
                between = text[mention['end']:modifier_start]
                distance = modifier_start - mention['end']
            else:
                between = ''
                distance = 0
            if distance <= 30 and not re.search(r'\band\b', between):
                candidates.append((distance, index))
        if candidates:
            _, closest = min(candidates)
            mentions[closest]['modifier_ids'].append(modifier_id)


def recommend_order(text: str, catalog: list[dict], across_restaurants=False) -> dict | None:
    """Return the best menu match, or None when no catalog item was recognized."""
    normalized = _normalize(text)
    mentions = _find_mentions(normalized, catalog)
    if not mentions:
        return None
    _attach_modifiers(normalized, mentions)

    if across_restaurants:
        named = [r for r in catalog if _normalize(r['name']) in normalized]
        basket, unmatched, owners = [], [], []
        for fragment in re.split(r'\band\b|,',normalized):
            fragment=fragment.strip()
            if not fragment or _find_mentions(fragment,catalog): continue
            if any(phrase in fragment for phrase in MODIFIERS): continue
            if fragment in {'please','thank you','thanks'}: continue
            # Do not silently omit a wholly unmatched part of a multi-item request.
            if len(re.split(r'\band\b|,',normalized))>1:
                unmatched.append(fragment)
        for mention in mentions:
            choices=[]
            for owner,product in mention['products']:
                if named and owner not in named: continue
                try:
                    line=price_line({'product_id':product['id'],'quantity':mention['quantity'],
                                     'modifier_ids':mention['modifier_ids']},owner['menu'])
                    choices.append((line,owner))
                except ValueError: continue
            if choices:
                line,owner=min(choices,key=lambda entry:(entry[0]['line_total_mad'],entry[0]['product_id']))
                basket.append(line); owners.append(owner)
            else: unmatched.append(mention['alias'])
        if not basket: return None
        return {'restaurant':owners[0],'basket':basket,
                'total_mad':round(sum(l['line_total_mad'] for l in basket),2),'unmatched_items':unmatched}

    candidates = []
    for restaurant in catalog:
        basket = []
        unmatched = []
        for mention in mentions:
            choices = [product for candidate_restaurant, product in mention['products']
                       if candidate_restaurant['id'] == restaurant['id']]
            priced_choices = []
            for product in choices:
                line = {
                    'product_id': product['id'],
                    'quantity': mention['quantity'],
                    'modifier_ids': mention['modifier_ids'],
                }
                try:
                    priced_choices.append((price_line(line, restaurant['menu']), product['name']))
                except (ValueError, TypeError, KeyError):
                    continue
            if priced_choices:
                line, _ = min(priced_choices, key=lambda choice: (choice[0]['line_total_mad'], choice[1]))
                basket.append(line)
            else:
                unmatched.append(mention['alias'])
        if basket:
            subtotal = round(sum(line['line_total_mad'] for line in basket), 2)
            candidates.append({
                'restaurant': restaurant,
                'basket': basket,
                'total_mad': subtotal,
                'unmatched_items': list(dict.fromkeys(unmatched)),
            })

    if not candidates:
        return None
    return min(candidates, key=lambda item: (-len(item['basket']), item['total_mad'], item['restaurant']['name'].casefold()))


async def recommend_with_ollama(text: str, catalog: list[dict]) -> dict | None:
    """Ask the local model to choose a restaurant and items, then reprice them."""
    from api.storage import search_catalog
    catalog = search_catalog(text, catalog)
    if not catalog: return None
    restaurants = {restaurant['id']: restaurant for restaurant in catalog}
    products = {
        product['id']: product
        for restaurant in catalog
        for product in restaurant['menu']
    }
    modifier_ids = sorted({
        modifier['id']
        for restaurant in catalog
        for product in restaurant['menu']
        for modifier in product.get('modifiers', [])
    })
    schema = ModelSelection.model_json_schema()
    schema['properties']['restaurant_id']['enum'] = list(restaurants)
    item_schema = schema['$defs'][SelectedItem.__name__]
    item_schema['properties']['product_id']['enum'] = list(products)
    item_schema['properties']['modifier_ids']['items']['enum'] = modifier_ids
    menu_context = [
        {
            'restaurant_id': restaurant['id'],
            'restaurant_name': restaurant['name'],
            'menu': [
                {
                    'product_id': product['id'],
                    'name': product['name'],
                    'price_mad': product['base_price_mad'],
                    'modifiers': [modifier['id'] for modifier in product.get('modifiers', [])],
                }
                for product in restaurant['menu']
            ],
        }
        for restaurant in catalog
    ]
    system = (
        'Build a proposed order from the complete restaurant catalog below. '
        'Understand casual phrasing and include every requested item exactly once, with its quantity and supported options. '
        'Choose one restaurant that covers the most requested items; break ties using the lowest listed food subtotal. '
        'Use only IDs in that restaurant menu. Put items you cannot find in unmatched_items. '
        'Never invent products, modifiers, prices, or confirm an order. The customer must review and confirm separately.\n'
        + json.dumps(menu_context, ensure_ascii=False)
    )
    payload = {
        'model': os.getenv('OLLAMA_MODEL', 'qwen3:4b'),
        'keep_alive': int(os.getenv('OLLAMA_KEEP_ALIVE', '-1')),
        'stream': False,
        'format': schema,
        'think': False,
        'options': {'temperature': 0, 'num_ctx': 4096, 'num_predict': 350},
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': text[:500]},
        ],
    }
    base_url = os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/')
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f'{base_url}/api/chat', json=payload)
            response.raise_for_status()
        content = response.json()['message']['content']
        selection = ModelSelection.model_validate_json(content)
        restaurant = restaurants.get(selection.restaurant_id)
        if restaurant is None:
            return None

        menu_ids = {product['id'] for product in restaurant['menu']}
        if any(item.product_id not in menu_ids for item in selection.items):
            return None
        if len({item.product_id for item in selection.items}) != len(selection.items):
            return None

        basket = [price_line(item.model_dump(), restaurant['menu']) for item in selection.items]
        total = round(sum(line['line_total_mad'] for line in basket), 2)
        return {
            'restaurant': restaurant,
            'basket': basket,
            'total_mad': total,
            'unmatched_items': [item for item in selection.unmatched_items if len(item)<=80 and _normalize(item) in _normalize(text)],
        }
    except httpx.HTTPStatusError as error:
        logger.warning('Ollama menu selection returned HTTP %s', error.response.status_code)
        return None
    except httpx.HTTPError as error:
        logger.warning('Ollama menu selection failed: %s', type(error).__name__)
        return None
    except (KeyError, TypeError, ValueError, ValidationError) as error:
        logger.warning('Ollama menu selection was invalid: %s', type(error).__name__)
        return None
