from typing import Dict, List, Optional, Any

def next_step(
    parsed: Optional[Dict[str, Any]], 
    basket: List[Dict[str, Any]], 
    state: str, 
    menu: List[Dict[str, Any]], 
    pending: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Évalue l'intention par rapport au menu, gère la logique de commande, 
    valide les quantités et modificateurs, et renvoie le contrat d'état complet.
    Ne modifie pas le panier en place (renvoie une copie).
    """
    if not parsed:
        parsed = {"intent": "unknown"}

    intent = parsed.get("intent", "unknown")
    product_id = parsed.get("product_id")
    quantity = parsed.get("quantity", 1)
    modifier_ids = parsed.get("modifier_ids", []) or []

    # Copie profonde du panier pour éviter toute modification en place
    new_basket = [dict(item) for item in basket]
    menu_dict = {item["id"]: item for item in menu}

    # 1. Validation rigoureuse des quantités (zéro, négatif, non-entier, trop grand)
    if quantity is not None:
        if not isinstance(quantity, int) or quantity <= 0 or quantity > 99:
            return {
                "state": "CLARIFY",
                "reply_text": "Quantité invalide. Veuillez préciser un nombre entre 1 et 99.",
                "basket": new_basket,
                "total_mad": sum(item["line_total_mad"] for item in new_basket),
                "question": "Quantité invalide",
                "pending": pending,
                "error": "Invalid quantity"
            }

    # Gestion du cas où une question précédente était en attente (pending)
    if pending and pending.get("missing_field") and intent not in ["cancel", "repeat", "confirm"]:
        # Résolution du champ manquant si l'utilisateur y répond
        missing_field = pending["missing_field"]
        prod_id = pending["product_id"]
        qty = pending["quantity"]
        
        product = menu_dict.get(prod_id)
        if product:
            mod_dict = {m["id"]: m for m in product.get("modifiers", [])}
            valid_mods = [m_id for m_id in modifier_ids if m_id in mod_dict]
            
            base_price = product["base_price_mad"]
            mod_delta = sum(mod_dict[m]["delta_mad"] for m in valid_mods)
            line_total = qty * (base_price + mod_delta)
            
            new_item = {
                "product_id": prod_id,
                "quantity": qty,
                "modifier_ids": valid_mods,
                "line_total_mad": line_total
            }
            new_basket.append(new_item)
            total_mad = sum(item["line_total_mad"] for item in new_basket)
            
            return {
                "state": "REVIEW",
                "reply_text": f"Ajouté : {qty} {product['name']}, {total_mad} dirhams au total. Confirmer, modifier ou annuler ?",
                "basket": new_basket,
                "total_mad": total_mad,
                "question": None,
                "pending": None,
                "error": None
            }

    if intent == "cancel":
        return {
            "state": "CANCELLED",
            "reply_text": "Commande annulée. Voulez-vous recommencer ?",
            "basket": new_basket,
            "total_mad": sum(item["line_total_mad"] for item in new_basket),
            "question": None,
            "pending": None,
            "error": None
        }

    if intent == "repeat":
        total = sum(item["line_total_mad"] for item in new_basket)
        return {
            "state": state,
            "reply_text": f"Votre panier actuel totalise {total} dirhams.",
            "basket": new_basket,
            "total_mad": total,
            "question": None,
            "pending": pending,
            "error": None
        }

    # 6. Confirmation uniquement depuis REVIEW et panier non vide
    if intent == "confirm":
        if state != "REVIEW":
            return {
                "state": state,
                "reply_text": "Il n'y a rien à confirmer pour l'instant.",
                "basket": new_basket,
                "total_mad": sum(item["line_total_mad"] for item in new_basket),
                "question": None,
                "pending": pending,
                "error": "Cannot confirm outside of REVIEW state"
            }
        if not new_basket:
            return {
                "state": state,
                "reply_text": "Votre panier est vide. Impossible de confirmer.",
                "basket": new_basket,
                "total_mad": 0,
                "question": None,
                "pending": pending,
                "error": "Cannot confirm empty basket"
            }
        
        total = sum(item["line_total_mad"] for item in new_basket)
        return {
            "state": "CONFIRMED",
            "reply_text": f"Commande confirmée ! Total de {total} dirhams. Merci !",
            "basket": new_basket,
            "total_mad": total,
            "question": None,
            "pending": None,
            "error": None
        }

    # 4. Implémentation de l'intention 'change' (correction au lieu d'ajouter bêtement)
    if intent == "change":
        if new_basket:
            new_basket.pop()  # Retire le dernier élément pour le modifier/remplacer
        return {
            "state": "REQUEST",
            "reply_text": "D'accord, que souhaitez-vous modifier ou commander à la place ?",
            "basket": new_basket,
            "total_mad": sum(item["line_total_mad"] for item in new_basket),
            "question": None,
            "pending": None,
            "error": None
        }

    # 5. Ne pas traiter product_id comme un 'add' si l'intention est 'unknown'
    if intent == "add" and product_id:
        if product_id not in menu_dict:
            return {
                "state": "CLARIFY",
                "reply_text": "Désolé, je n'ai pas trouvé ce produit sur le menu. Pouvez-vous répéter ?",
                "basket": new_basket,
                "total_mad": sum(item["line_total_mad"] for item in new_basket),
                "question": "Produit inconnu",
                "pending": None,
                "error": "Unknown product_id"
            }
        
        product = menu_dict[product_id]
        
        # 2. Ne pas supprimer silencieusement les modificateurs inconnus -> Retourner CLARIFY
        mod_dict = {m["id"]: m for m in product.get("modifiers", [])}
        for mid in modifier_ids:
            if mid not in mod_dict:
                return {
                    "state": "CLARIFY",
                    "reply_text": f"Option inconnue '{mid}' pour ce produit. Pouvez-vous préciser ?",
                    "basket": new_basket,
                    "total_mad": sum(item["line_total_mad"] for item in new_basket),
                    "question": f"Modificateur inconnu: {mid}",
                    "pending": None,
                    "error": "Unknown modifier_id"
                }

        base_price = product["base_price_mad"]
        mod_delta = sum(mod_dict[mid]["delta_mad"] for mid in modifier_ids)
        line_total = quantity * (base_price + mod_delta)

        # 3. Vérification des options manquantes (missing_field / pending) si nécessaire
        # (Exemple de logique de champ obligatoire si requis par le produit)
        if product.get("requires_size") and "large" not in modifier_ids and "small" not in modifier_ids:
            pending_obj = {"product_id": product_id, "quantity": quantity, "missing_field": "size"}
            return {
                "state": "CLARIFY",
                "reply_text": "Quelle taille souhaitez-vous ?",
                "basket": new_basket,
                "total_mad": sum(item["line_total_mad"] for item in new_basket),
                "question": "Préciser la taille",
                "pending": pending_obj,
                "error": None
            }

        new_item = {
            "product_id": product_id,
            "quantity": quantity,
            "modifier_ids": modifier_ids,
            "line_total_mad": line_total
        }
        new_basket.append(new_item)
        total_mad = sum(item["line_total_mad"] for item in new_basket)

        return {
            "state": "REVIEW",
            "reply_text": f"Ajouté : {quantity} {product['name']}, {total_mad} dirhams au total. Confirmer, modifier ou annuler ?",
            "basket": new_basket,
            "total_mad": total_mad,
            "question": None,
            "pending": None,
            "error": None
        }

    # Échec du modèle ou intention inconnue
    return {
        "state": "CLARIFY",
        "reply_text": "Je n'ai pas bien compris. Pouvez-vous reformuler votre commande ?",
        "basket": new_basket,
        "total_mad": sum(item["line_total_mad"] for item in new_basket),
        "question": "Clarification requise",
        "pending": pending,
        "error": "Unclear intent"
    }