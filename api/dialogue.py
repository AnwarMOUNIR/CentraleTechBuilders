"""Grounded dialogue actions that must not depend on model improvisation."""
import re
from api.catalog import CATALOG, get_product_and_restaurant
from api.interpreter_mock import normalize, explicit_confirmation
from api.recommendation import MODIFIERS, GENERIC_TERMS, QUANTITIES, recommend_order, _find_mentions, _normalize
from api.storage import search_catalog, conversation_context
from api.recommendation import spoken_order_lines

def inquiry(text):
    return {'intent':'inquiry', 'suggestion_or_question':text}

def route(text, basket, pending, restaurant):
    s = normalize(text)
    if explicit_confirmation(text): return {'intent':'confirm'}
    if re.search(r'\b(dont|do not|never) (cancel|remove|delete)\b',s):
        return inquiry('Your basket is unchanged. Tell me what you would like to do next.')
    if re.search(r'\b(dont want|do not want|not ordering|not order|dont add|do not add|instead of)\b',s) or re.match(r'^no (coffee|tea|sandwich|pizza|pastilla)\b',s):
        return inquiry('I have not added anything. Say remove followed by the item name to remove it, or tell me the item you do want.')
    if re.search(r'\b(allerg\w*|gluten|nut free|halal|vegan|vegetarian|ingredients)\b', s):
        return inquiry('I cannot verify ingredients, allergens, or dietary suitability from these sample menus. Please check directly with the restaurant. I have not changed your basket.')
    if re.search(r'\b(payment|pay|card|address|deliver|delivery|arrive|available now|open now)\b', s):
        return inquiry('This is a simulated order. I cannot check live stock, opening hours or delivery, take payment, or send an order. Totals are food subtotals only.')
    if s in {'yes','yes please','sure','okay','ok','go ahead','add it','add that','sounds good'}:
        if pending and pending.get('missing_field')=='proposal': return {'intent':'accept_proposal'}
        if pending and pending.get('missing_field') == 'offer':
            return {'intent':'accept_offer', **{k:pending[k] for k in ('product_id','quantity','modifier_ids')}}
        return inquiry('Say the item you want to add or change. If you are ready to place this simulated order, say confirm order.')
    if pending and pending.get('missing_field') in {'offer','proposal'} and s in {'no','no thanks','not that','no thank you'}:
        return {'intent':'decline_offer'}
    if s in {'cancel','cancel order','cancel my order','never mind','nevermind','start over','clear basket','clear my basket'}:
        return {'intent':'cancel'}
    if re.search(r'\b(heart rate|heartbreak|heart break)\b',s):
        recent=' '.join(m['content'].lower() for m in conversation_context.get())
        if 'hot drink' in recent or (pending and pending.get('missing_field')=='proposal'):
            return inquiry('I may have misheard hot drink. Please repeat hot drink clearly. Your basket and full proposal are unchanged. Say yes only if you want to add the full proposal, or no to decline it.')
        return inquiry('I may have misheard. Please name a menu item or say menu. Your basket is unchanged.')
    if re.search(r'\b(hot|warm|cold|cool|chilled) (drink|beverage)s?\b',s):
        if pending and pending.get('missing_field')=='proposal' and pending.get('proposal_items'):
            from api.logic import price_line
            items=[price_line(item) for item in pending['proposal_items']]
            selection={'restaurant':get_product_and_restaurant(items[0]['product_id'])[0],
                       'basket':items,'total_mad':round(sum(i['line_total_mad'] for i in items),2),'unmatched_items':[]}
            return {'intent':'proposal','items':items,'suggestion_or_question':
                    'Your full proposal is still waiting. '+spoken_order_lines(selection)+
                    ' Say yes to add all of it, or no to decline and choose different items. Nothing has been added yet.'}
        if re.search(r'\b(zero|hundred|thousand|minus|negative)\b',s) or any(int(n)>99 or int(n)==0 for n in re.findall(r'\b\d+\b',s)) or re.search(r'(?<!\w)-\d|\d+\.\d+',text):
            return inquiry('Please use a whole-number quantity between one and 99. Your basket is unchanged.')
        if re.match(r'^(why|what happened|where is)\b',s):
            return inquiry('Category choices are suggestions until you accept them. Say hot drink or cold drink to hear a proposal, or name the dish you prefer. Your basket is unchanged.')
        expanded=re.sub(r'\b(hot|warm) (drink|beverage)s?\b','coffee',text,flags=re.I)
        expanded=re.sub(r'\b(cold|cool|chilled) (drink|beverage)s?\b','orange juice',expanded,flags=re.I)
        selection=recommend_order(expanded,CATALOG,across_restaurants=True)
        if not selection: return inquiry('For a hot drink you can choose coffee or tea. For a cold drink, orange juice or water. What would you prefer?')
        if selection['unmatched_items']:
            return inquiry('I can suggest coffee for a hot drink and orange juice for a cold drink, but I could not match every part of your request. Please clarify the other items. Your basket is unchanged.')
        return {'intent':'proposal','items':selection['basket'], 'suggestion_or_question':
                'I suggest coffee for a hot drink and orange juice for a cold drink where requested. '+spoken_order_lines(selection)+
                ' These are suggestions, not yet added. Say yes to add all these items, or no to decline and choose other items.'}
    if s in {'repeat','repeat that','say that again','read my order','what did i order','whats in my basket','what is in my basket','what is my total','how much is my order','what is the total'}:
        return {'intent':'repeat'}
    if pending and pending.get('missing_field')=='proposal':
        return inquiry('Your proposed items are still waiting; I have not added or removed anything. Say yes to add the full proposal, or no to decline it and choose other items.')
    if re.match(r'^(remove|delete|take off|take out)\b', s):
        if not basket: return inquiry('Your basket is empty. What would you like to order?')
        if re.search(r'\b(last|that|it)\b',s): return {'intent':'remove','product_id':basket[-1]['product_id']}
        choices = search_catalog(text,CATALOG,basket=[])
        ids={p['id'] for r in choices for p in r['menu']}
        matches=[b for b in basket if b['product_id'] in ids]
        if len(matches)==1: return {'intent':'remove','product_id':matches[0]['product_id']}
        return inquiry('Which basket item should I remove? Please say its full name or say remove the last item.')
    if re.search(r'\b(menu|menus|restaurants)\b',s) and not re.search(r'\b(add|order|want|like)\b',s) or s in {'help','what can i order','what do you have','what can i get','what are my options'}:
        selected = next((r for r in CATALOG if normalize(r['name']) in s), None)
        if selected:
            return inquiry(selected['name'] + ': ' + '; '.join(f"{p['name']}, {p['base_price_mad']:g} dirhams" for p in selected['menu']) + '. Tell me what you would like.')
        return inquiry('Here are the sample menus. ' + ' '.join(r['name'] + ': ' + ', '.join(p['name'] for p in r['menu'][:3]) + '.' for r in CATALOG) + ' Ask about a dish, or say the restaurant name and menu.')
    if re.match(r'^(do you|is there|are there|can you|could you|which|where|how much|what.*(?:offer|serve|recommend))\b',s) and not re.search(r'\b(add|order|give|get|bring|make|change|remove)\b',s):
        selection = recommend_order(text,CATALOG,across_restaurants=True)
        if selection and selection['basket']:
            item=selection['basket'][0]
            r,p=get_product_and_restaurant(item['product_id'])
            return {'intent':'offer','product_id':p['id'],'quantity':1,'modifier_ids':[],
                    'suggestion_or_question':f"{r['name']} lists {p['name']} at {p['base_price_mad']:g} dirhams. This is a sample price, not live availability. Would you like to add one?"}
        return inquiry('I could not find a matching dish in the sample catalog. Say menu to hear examples, or name a dish. Your basket is unchanged.')
    if re.search(r'\b(zero|hundred|thousand|minus|negative)\b',s) or any(int(n)>99 or int(n)==0 for n in re.findall(r'\b\d+\b',s)) or re.search(r'(?<!\w)-\d|\d+\.\d+',text):
        return inquiry('Please use a whole-number quantity between one and 99. Your basket is unchanged.')
    normalized=_normalize(text)
    harmless=set(QUANTITIES) | {'want','like','order','add','have','get','some','any','the','of','and','with','another','please','me','more','delicious','tasty','big','small','large','spicy'}
    harmless.update(word for phrase in MODIFIERS for word in phrase.split())
    for mention in _find_mentions(normalized,CATALOG):
        prefix=normalized[:mention['start']].split()
        if mention['alias'] in GENERIC_TERMS and prefix:
            qualifier=prefix[-1]
            if qualifier not in harmless and not qualifier.isdigit() and not any(
                qualifier in _normalize(p['name']).split() for _,p in mention['products']):
                return inquiry(f'I could not match {qualifier} {mention["alias"]} exactly in the sample menu. Please name an available item or say menu. Your basket is unchanged.')
    return None

def explicit_modifiers(text):
    s=normalize(text)
    result={mid for phrase,mid in MODIFIERS.items() if re.search(r'\b'+re.escape(phrase)+r'\b',s)}
    if re.search(r'\b(big|bigger)\b',s): result.add('large')
    return result

def constrain(parsed,text):
    """Valid menu options are still forbidden unless requested by the user."""
    allowed=explicit_modifiers(text)
    if 'unmatched_items' in parsed:
        parsed['unmatched_items']=[term for term in parsed['unmatched_items']
                                  if isinstance(term,str) and len(term)<=80 and normalize(term) in normalize(text)]
    if re.search(r'\b(not spicy|no spice|without spice|without spicy)\b',normalize(text)):
        allowed.discard('spicy')
        parsed['remove_modifier_ids']=['spicy']
    if parsed.get('intent')=='change' and not re.search(r'\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b',normalize(text)):
        parsed['quantity']=None
    for item in [parsed,*parsed.get('items',[])]:
        if 'modifier_ids' in item:
            item['modifier_ids']=[m for m in item['modifier_ids'] if m in allowed]
    return parsed
