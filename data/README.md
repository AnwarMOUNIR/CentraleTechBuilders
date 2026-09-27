# Bouskoura restaurant seed data

`bouskoura_restaurants.json` is a sourced prototype dataset for discovery and ordering-flow demonstrations. It contains a representative subset of publicly listed menu items rather than complete restaurant menus.

## Important limits

- Prices, promotions, availability, ratings, delivery fees and delivery estimates can change without notice.
- Delivery time depends on the exact address, time, traffic, restaurant load and platform. A missing estimate is represented by `null`; the application must not invent one.
- `estimated_total_mad` is `null` whenever a required fee is unknown.
- Restaurant and platform names remain the property of their respective owners. This dataset does not imply a partnership or live integration.
- Do not place real orders from this prototype. Re-check the source provider before showing any information as current.

The main hackathon flow still uses the small frozen menu in `shared/menu.json`. Integrating this multi-restaurant dataset requires a reviewed contract change because basket lines would need a `restaurant_id` and decimal-price handling.
