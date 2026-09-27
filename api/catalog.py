"""English display menu over the preserved, sourced restaurant snapshot."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_MENU = json.loads((ROOT / 'shared/menu.json').read_text(encoding='utf-8'))
DATA = json.loads((ROOT / 'data/bouskoura_restaurants.json').read_text(encoding='utf-8'))
ENGLISH = [
    ['Burger meal with soda and dessert', 'Taco meal with fries soda and dessert', 'Moroccan salad', 'Chicken nugget taco', 'Margherita pizza', 'Vegetarian pizza'],
    ['Black coffee', 'Tea', 'Cheeseburger with fries', 'Margherita pizza', 'Chicken and mushroom pasta', 'Orange juice'],
    ['Minced beef sandwich', 'Breaded chicken sandwich', 'Fish pastilla', 'Beef briouates', 'Minced steak', 'Orange juice'],
    ['Eggplant parmigiana', 'House salad', 'Mozzarella sticks', 'Beef carpaccio', 'Chicken Caesar salad', 'Verdura salad'],
    ['Baba Ghanouch', 'Acili Ezme', 'Mutabel', 'Atom'],
    ['Chicken pitta meal', 'Yony burger', 'Seafood pizza', 'Double cheeseburger', 'Chicken Caesar salad', 'Fisherman salad'],
]

CATALOG = [dict(id='demo', name='ClearOrder Demo Cafe', menu=DEMO_MENU, delivery=None,
                note='Simulated cafe menu. No payment or delivery.', source=None)]
for restaurant, names in zip(DATA['restaurants'], ENGLISH):
    CATALOG.append(dict(
        id=restaurant['id'], name=restaurant['name'],
        menu=[dict(id=item['id'], name=name, base_price_mad=item['price_mad'], modifiers=[])
              for item, name in zip(restaurant['menu'], names)],
        delivery=restaurant['delivery'], source=restaurant['source'],
        note='Sampled public menu; prices and delivery estimates are unverified snapshots. No real order is placed.',
    ))

def get_restaurant(restaurant_id):
    return next((r for r in CATALOG if r['id'] == restaurant_id), None)

CATALOG_PRODUCTS = {
    product['id']: (restaurant, product)
    for restaurant in CATALOG
    for product in restaurant['menu']
}

def get_product_and_restaurant(product_id: str):
    return CATALOG_PRODUCTS.get(product_id)

def get_restaurant_for_product(product_id: str):
    pair = CATALOG_PRODUCTS.get(product_id)
    return pair[0] if pair else None
