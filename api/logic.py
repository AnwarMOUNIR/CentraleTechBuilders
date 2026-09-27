"""Deterministic demo ordering; every price is recomputed from the menu."""
from copy import deepcopy
from decimal import Decimal


def price_line(line, menu=None):
    from api.catalog import get_product_and_restaurant
    product = None
    if menu:
        product = next((p for p in menu if p['id'] == line.get('product_id')), None)
    if product is None:
        pair = get_product_and_restaurant(line.get('product_id'))
        if pair:
            product = pair[1]
    if product is None:
        raise ValueError('Unknown product_id')
    quantity = line.get('quantity')
    if type(quantity) is not int or not 1 <= quantity <= 99:
        raise ValueError('Invalid quantity')
    mods = line.get('modifier_ids', [])
    if not isinstance(mods, list) or any(not isinstance(m, str) for m in mods):
        raise ValueError('Unknown modifier_id')
    mods = list(dict.fromkeys(mods))
    available = {m['id']: m for m in product.get('modifiers', [])}
    if any(m not in available for m in mods):
        raise ValueError('Unknown modifier_id')
    if {'small', 'large'} <= set(mods) or {'no_sugar', 'extra_sugar'} <= set(mods):
        raise ValueError('Conflicting options')
    price = Decimal(str(product['base_price_mad']))
    price += sum((Decimal(str(available[m]['delta_mad'])) for m in mods), Decimal(0))
    return dict(product_id=product['id'], quantity=quantity, modifier_ids=mods,
                line_total_mad=float((price * quantity).quantize(Decimal('.01'))))


def summary(basket, menu=None):
    from api.catalog import get_product_and_restaurant
    parts = []
    for line in basket:
        product = None
        if menu:
            product = next((p for p in menu if p['id'] == line.get('product_id')), None)
        if product is None:
            pair = get_product_and_restaurant(line.get('product_id'))
            if pair:
                product = pair[1]
        if not product:
            continue
        labels = {m['id']: m['label'] for m in product.get('modifiers', [])}
        options = ', '.join(labels[m] for m in line.get('modifier_ids', []) if m in labels)
        parts.append(f"{line['quantity']} {product['name']}" + (f", {options}" if options else '')
                     + f", {line['line_total_mad']:g} dirhams")
    total = round(sum(line['line_total_mad'] for line in basket), 2)
    return ('; '.join(parts) + '. ' if parts else 'Your basket is empty. ') + f'Total: {total:g} dirhams.'


def next_step(parsed, basket, state, menu, pending=None):
    parsed = parsed if isinstance(parsed, dict) else {'intent': 'unknown'}
    proposal_items = deepcopy(pending.get('proposal_items')) if pending else None
    pending = ({k: deepcopy(pending.get(k)) for k in
                ('product_id', 'quantity', 'modifier_ids', 'missing_field')} if pending else None)
    if pending:
        pending['modifier_ids'] = pending['modifier_ids'] or []
        if proposal_items is not None: pending['proposal_items'] = proposal_items
    lines = []
    invalid_basket = False
    for line in basket:
        try:
            lines.append(price_line(line, menu))
        except (ValueError, TypeError, KeyError):
            invalid_basket = True

    def response(next_state, reply, question=None, error=None, next_pending=pending):
        return dict(state=next_state, reply_text=reply, basket=deepcopy(lines),
                    total_mad=round(sum(l['line_total_mad'] for l in lines), 2),
                    question=question, pending=deepcopy(next_pending), error=error)

    def clarify(error, item=pending, question='Please clarify your order.'):
        return response('CLARIFY', question, question, error, item)

    intent = parsed.get('intent', 'unknown')
    if invalid_basket and intent != 'cancel':
        return clarify('Invalid basket item removed; review required', question='An unavailable or invalid item was removed. Your other items are preserved. ' + summary(lines, menu) + ' Please review or update the order before confirming.')
    if intent == 'cancel':
        lines = []
        return response('CANCELLED', 'Simulated order cancelled. No order was placed.', next_pending=None)
    if intent == 'proposal':
        offer={'product_id':None,'quantity':None,'modifier_ids':[], 'missing_field':'proposal',
               'proposal_items':parsed['items']}
        return response('CLARIFY',parsed['suggestion_or_question'],next_pending=offer)
    if intent == 'accept_proposal':
        if not pending or pending.get('missing_field')!='proposal': return clarify('No pending proposal')
        try:
            proposed=[price_line(item,menu) for item in pending.get('proposal_items',[])]
        except (ValueError,TypeError,KeyError):
            return clarify('Invalid proposal',question='Please name the items again.')
        if not proposed or len(lines)+len(proposed)>20: return clarify('Basket limit or empty proposal')
        lines.extend(proposed)
        return response('REVIEW',summary(lines,menu)+' Say confirm order, change, or cancel.',next_pending=None)
    if intent == 'offer':
        offer={k:parsed.get(k) for k in ('product_id','quantity','modifier_ids')}
        offer['missing_field']='offer'
        return response('CLARIFY',parsed['suggestion_or_question'],next_pending=offer)
    if intent == 'decline_offer':
        return response('REVIEW' if lines else 'REQUEST','I have not added it. ' + summary(lines,menu),next_pending=None)
    if intent == 'accept_offer':
        pending=None
        intent='add'
    if intent == 'remove':
        matches=[i for i,l in enumerate(lines) if l['product_id']==parsed.get('product_id')]
        if len(matches)!=1: return clarify('Ambiguous removal',question='Please specify exactly which basket item to remove.')
        lines.pop(matches[0])
        return response('REVIEW' if lines else 'REQUEST','Item removed. ' + summary(lines,menu),next_pending=None)
    if intent == 'repeat':
        if pending and pending.get('missing_field')=='proposal':
            proposed=[price_line(item,menu) for item in pending.get('proposal_items',[])]
            return response(state,'Your proposed additions, not yet added: '+summary(proposed,menu)+
                            ' Say yes to add them or no to decline. Current basket: '+summary(lines,menu))
        question = ('Please answer the pending question before confirming.' if pending else '')
        return response(state, summary(lines, menu) + ' ' + question, next_pending=pending)
    if intent == 'confirm':
        if state != 'REVIEW':
            return response(state, 'Please complete your order and review it first.',
                            error='Cannot confirm outside of REVIEW state')
        if not lines:
            return response(state, 'Your basket is empty.', error='Cannot confirm empty basket')
        if pending:
            return clarify('Pending clarification', question='Please finish the requested change first.')
        return response('CONFIRMED', 'Simulated order confirmed. ' + summary(lines, menu)
                        + ' No payment or delivery will take place.', next_pending=None)
    if intent == 'inquiry':
        suggestion = parsed.get('suggestion_or_question') or 'How can I help with your order?'
        return response('REVIEW' if lines and not pending else 'CLARIFY', suggestion, question=suggestion, error=None, next_pending=pending)
    if intent not in {'add', 'change'}:
        return clarify('Unclear pending answer' if pending else 'Unclear intent',
                       question='Please name one menu item or say help.')

    if intent == 'add' and parsed.get('items') and isinstance(parsed['items'], list) and len(parsed['items']) > 0:
        if len(lines)+len(parsed['items'])>20:
            return clarify('Basket limit',question='This demo supports up to 20 basket lines. Please remove an item first.')
        added_lines = []
        for it in parsed['items']:
            from api.catalog import get_product_and_restaurant
            if not get_product_and_restaurant(it.get('product_id')) and not any(p['id'] == it.get('product_id') for p in menu):
                continue
            try:
                line = price_line(it, menu)
                lines.append(line)
                added_lines.append(line)
            except (ValueError, TypeError, KeyError):
                continue
        if added_lines:
            unmatched_note = ''
            if parsed.get('unmatched_items'):
                included_words = set()
                for line in lines:
                    pair = get_product_and_restaurant(line['product_id'])
                    if pair: included_words.update(pair[1]['name'].lower().split())
                unmatched = [word for word in parsed['unmatched_items']
                             if not set(str(word).lower().split()) <= included_words]
                if unmatched:
                    unmatched_note = ' (Note: I could not match ' + ', '.join(unmatched) + ' in this proposal).'
            return response('REVIEW', summary(lines, menu) + unmatched_note + ' Say confirm order, change, add another item, or cancel.', next_pending=None)

    item = dict(product_id=parsed.get('product_id'), quantity=parsed.get('quantity', 1),
                modifier_ids=deepcopy(parsed.get('modifier_ids') or []), missing_field=None)
    changing = intent == 'change' or bool(pending and pending['missing_field'] == 'change')
    target = len(lines) - 1
    if changing:
        if not lines:
            return clarify('Cannot change empty basket', question='Your basket is empty. What would you like?')
        if item['product_id']:
            matches = [i for i, l in enumerate(lines) if l['product_id'] == item['product_id']]
            if len(matches) != 1:
                return clarify('Ambiguous change', question='Please change the last item by saying make that two, or cancel and start again.')
            target = matches[0]
        old = lines[target]
        if not item['product_id'] and parsed.get('quantity') is None and not item['modifier_ids'] and not parsed.get('remove_modifier_ids'):
            return clarify(None, {**old, 'missing_field': 'change'}, 'What would you like to change?')
        item['product_id'] = item['product_id'] or old['product_id']
        item['quantity'] = parsed.get('quantity') if parsed.get('quantity') is not None else old['quantity']
        mods = [m for m in old['modifier_ids'] if m not in parsed.get('remove_modifier_ids',[])]
        for mid in item['modifier_ids']:
            group = {'large', 'small'} if mid in {'large', 'small'} else {'no_sugar', 'extra_sugar'} if mid in {'no_sugar', 'extra_sugar'} else {mid}
            mods = [m for m in mods if m not in group] + [mid]
        item['modifier_ids'] = mods
    elif pending:
        field = pending['missing_field']
        item['product_id'] = parsed.get('product_id') or pending['product_id']
        item['quantity'] = parsed.get('quantity') if field in {'quantity', 'qty'} else pending['quantity']
        item['modifier_ids'] = list(dict.fromkeys(pending['modifier_ids'] + item['modifier_ids']))
        if field in {'modifier', 'modifiers', 'size'} and not parsed.get('modifier_ids'):
            return clarify('Unclear pending answer')
        if field == 'size' and not {'small', 'large'} & set(item['modifier_ids']):
            return clarify('Unclear pending answer', question='Small or large?')

    from api.catalog import get_product_and_restaurant
    if not get_product_and_restaurant(item['product_id']) and not any(p['id'] == item['product_id'] for p in menu):
        return clarify('Unknown product_id', question='Which item from the menu would you like?')
    if item['quantity'] is None:
        item['missing_field'] = 'quantity'
        return clarify(None, item, 'What quantity would you like?')
    if parsed.get('missing_field') and not pending and not changing:
        item['missing_field'] = parsed['missing_field']
        return clarify(None, item, 'Small or large?' if item['missing_field'] == 'size' else 'Which option would you like?')
    try:
        line = price_line(item, menu)
    except ValueError as exc:
        return clarify(str(exc), pending, 'Please specify a valid quantity and available menu options.')
    if changing:
        lines[target] = line
    else:
        if len(lines)>=20:
            return clarify('Basket limit',question='This demo supports up to 20 basket lines. Please remove an item first.')
        lines.append(line)
    return response('REVIEW', summary(lines, menu) + ' Say confirm order, change, add another item, or cancel.', next_pending=None)
