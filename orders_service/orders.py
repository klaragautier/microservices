# orders_service/orders.py
# Rôle : gérer la logique panier, paiement et commandes.


from flask import Flask, request, jsonify
import random
import json
import datetime
import os
 
orders_app = Flask(__name__)



# --- Données initiales par défaut (utilisées si les fichiers n'existent pas) ---
# On laisse vide car l'utilisateur doit créer son compte
DEFAULT_ORDERS = {}
# --- Configuration des fichiers de données ---
ORDERS_FILE = 'orders.json' # Fichier pour les commandes



# --- Catalogue des produits (Pour validation et calcul des prix) ---
PRODUCTS = {
    "Fraises": 2.50,
    "Haricots": 1.80,
    "Laine": 12.00,
    "Peches": 3.00,
    "Pasteques": 7.00,
    "Pates": 1.20
}




# --- Fonctions de gestion des fichiers JSON ---
def load_orders():
    try:
        with open(ORDERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_orders(data):
    with open(ORDERS_FILE, "w") as f:
        json.dump(data, f, indent=4)


# --- Fonction : Initialisation des fichiers au démarrage ---
if not os.path.exists(ORDERS_FILE):
    save_orders({})


# --- Récupérer la commande ---
@orders_app.route("/orders/<username>", methods=["GET"])
def get_orders(username):
    data = load_orders()
    return jsonify(data.get(username, [])), 200

# --- Créer une commande ---
@orders_app.route("/submit_order/<user>", methods=["POST"])
def submit_order(user):
    cart_items = []
    has_items = False

    # Lire les quantités envoyées depuis le formulaire gateway
    for item_name, unit_price in PRODUCTS.items():
        try:
            quantity = int(request.form.get(item_name, 0))
        except:
            quantity = 0

        if quantity > 0:
            cart_items.append({
                "article": item_name,
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": round(quantity * unit_price, 2)
            })
            has_items = True

    if not has_items:
        return jsonify({
            "redirect_url": f"/accueil?user={user}&error_message=Votre+panier+est+vide"
        })

    return process_payment(user, cart_items)


# --- Processus de paiement ---
def process_payment(user, cart_items):
    total_amount = round(sum(item["total_price"] for item in cart_items), 2)

    # Simuler un paiement (1 chance sur 2)
    success = random.random() < 0.5

    if success:
        orders = load_orders()

        if user not in orders:
            orders[user] = []

        new_order = {
            "order_id": str(datetime.datetime.now().timestamp()).replace(".", ""),
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total": total_amount,
            "items": cart_items
        }

        orders[user].append(new_order)
        save_orders(orders)

        status = "ok"
    else:
        status = "error"

    # Le microservice NE REDIRIGE PAS → il renvoie l'URL au gateway
    return jsonify({
        "redirect_url": f"/achat?status={status}&user={user}"
                        f"&total={total_amount}"
                        f"&details={json.dumps(cart_items)}"
    })

