def next_step(parsed: dict, basket: list, state: str, menu: list, pending: dict | None) -> dict:
    intent = parsed.get("intent", "unknown")
    product_id = parsed.get("product_id")
    quantity = parsed.get("quantity", 1) or 1
    modifier_ids = parsed.get("modifier_ids", []) or []

    menu_dict = {item["id"]: item for item in menu}

    error = None
    question = None

    if intent == "cancel":
        return {
            "state": "CANCELLED",
            "reply_text": "Commande annulée. Voulez-vous recommencer ?",
            "basket": basket,
            "total_mad": sum(item["line_total_mad"] for item in basket),
            "question": None,
            "pending": None,
            "error": None
        }

    if intent == "repeat":
        total = sum(item["line_total_mad"] for item in basket)
        return {
            "state": state,
            "reply_text": f"Votre panier actuel totalise {total} dirhams.",
            "basket": basket,
            "total_mad": total,
            "question": question,
            "pending": pending,
            "error": error
        }

    if intent == "confirm":
        if state == "REVIEW":
            total = sum(item["line_total_mad"] for item in basket)
            return {
                "state": "CONFIRMED",
                "reply_text": f"Commande confirmée ! Total de {total} dirhams. Merci !",
                "basket": basket,
                "total_mad": total,
                "question": None,
                "pending": None,
                "error": None
            }
        else:
            return {
                "state": state,
                "reply_text": "Il n'y a rien à confirmer pour l'instant. Que souhaitez-vous commander ?",
                "basket": basket,
                "total_mad": sum(item["line_total_mad"] for item in basket),
                "question": None,
                "pending": pending,
                "error": "Cannot confirm outside of REVIEW state"
            }

    if intent == "add" or product_id:
        if product_id not in menu_dict:
            return {
                "state": "CLARIFY",
                "reply_text": "Désolé, je n'ai pas trouvé ce produit sur le menu. Pouvez-vous répéter ?",
                "basket": basket,
                "total_mad": sum(item["line_total_mad"] for item in basket),
                "question": "Produit inconnu",
                "pending": None,
                "error": "Unknown product_id"
            }
        
        product = menu_dict[product_id]
        base_price = product["base_price_mad"]
        
        valid_modifier_ids = []
        mod_dict = {m["id"]: m for m in product.get("modifiers", [])}
        modifier_delta = 0
        
        for mid in modifier_ids:
            if mid in mod_dict:
                valid_modifier_ids.append(mid)
                modifier_delta += mod_dict[mid]["delta_mad"]

        line_total = quantity * (base_price + modifier_delta)

        new_item = {
            "product_id": product_id,
            "quantity": quantity,
            "modifier_ids": valid_modifier_ids,
            "line_total_mad": line_total
        }
        basket.append(new_item)
        total_mad = sum(item["line_total_mad"] for item in basket)

        reply_text = f"Ajouté : {quantity} {product['name']}, {total_mad} dirhams au total. Confirmer, modifier ou annuler ?"
        
        return {
            "state": "REVIEW",
            "reply_text": reply_text,
            "basket": basket,
            "total_mad": total_mad,
            "question": None,
            "pending": None,
            "error": None
        }

    return {
        "state": "CLARIFY",
        "reply_text": "Je n'ai pas bien compris. Pouvez-vous reformuler votre commande ?",
        "basket": basket,
        "total_mad": sum(item["line_total_mad"] for item in basket),
        "question": "Clarification requise",
        "pending": pending,
        "error": "Unclear intent"
    }