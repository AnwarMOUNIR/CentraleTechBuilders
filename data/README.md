# English demo restaurant seed data

`bouskoura_restaurants.json` is a demo-only catalog for restaurant matching and ordering-flow demonstrations. Every restaurant display name is fictional and English. The menus and prices are illustrative snapshots adapted from public listings; the source URLs are retained only as data provenance and do not identify or imply a partnership with the fictional names.

## Important limits

- Prices, promotions, availability, ratings, delivery fees and delivery estimates are sample data and may be stale or incomplete.
- Delivery time depends on the exact address, time, traffic, restaurant load and platform. A missing estimate is represented by `null`; the application must not invent one.
- `estimated_total_mad` is `null` whenever a required fee is unknown.
- Fictional restaurant names are not real merchants. Source platforms are listed only to document the origin of sample menu data; there is no partnership or live integration.
- Do not place real orders from this prototype. Re-check the source provider before showing any information as current.

The main hackathon flow still uses the small frozen menu in `shared/menu.json`. Integrating this multi-restaurant dataset requires a reviewed contract change because basket lines would need a `restaurant_id` and decimal-price handling.
