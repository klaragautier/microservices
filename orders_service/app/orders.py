# Order Service : gère les achats/commandes 
# accèpte les requêtes que si le JWT est valide.


# os est un module python qui sert à parler avec le système d'exploitation
# il permet de vérifier si un fichier existe, créer des dossiers, gérer des envinronnements..
from app import app
from flask import jsonify, request
import os
import json
import jwt


# Liste des articles du magasin
ARTICLES = {
    "Fraises": 2.50,
    "Framboises": 1.80,
    "Mures": 2.00,
    "Peches": 3.00,
    "Pasteques": 3.00,
    "Mirtilles": 1.20
}

# Fichier qui permet de sauvegarder l'historique des commandes
orders_file = "/app/orders_data/orders_data.json"

# Fonction pour sauvegarder les commandes dans un fichier
# Si le fichier n'existe pas, on le crée et on initialise une liste vide
# On va ajouter la nouvelle commande à l'historique
def save_order_data(order):
    # 1) S'assurer que le dossier existe
    os.makedirs(os.path.dirname(orders_file), exist_ok=True)

    # 2) S'assurer que le fichier existe sinon en créer un vide
    if not os.path.exists(orders_file):
        with open(orders_file, 'w') as f:
            json.dump([], f)

    # 3) Charger le contenu existant ou liste vide si cassé
    try:
        with open(orders_file, 'r') as f:
            orders_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        orders_data = []

    # 4) Ajouter la commande
    orders_data.append(order)

    # 5) Sauvegarder
    with open(orders_file, 'w') as f:
        json.dump(orders_data, f, indent=4)


# Fonction pour vérifier le token
def verify_access_token():
    token = request.headers.get("Authorization")

    if not token:
        return None

    token = token.replace("Bearer ", "")

    try:
        payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        return payload["sub"]  # username
    except:
        return None



# Envoyer la liste des articles au Gateway
@app.route("/articles")
def get_articles():
    return jsonify(ARTICLES), 200



# Recevoir et calculer le panier
# On va vérifier le token d'accès
# Si le token est invalide, on renvoie une erreur 401 (Unauthorized)
# order = request.get_json() : Le gateway va envoyer un JSON avec les articles et quantités
# Pour chaque article dans le panier, si la quantité est > 0
# on va chercher le prix dans la liste ARTICLES
# on va calculer le sous-total en multipliant le prix par la quantité, puis on l'ajoute au total
# on ajoute une ligne dans details qui contient l'article, la quantité, le prix unitaire et le sous-total
# 200 est le code HTTP pour "OK"
@app.route("/orders", methods=["POST"])
def get_orders():
    """user = verify_access_token()
    if user is None:
        return {"error": "Token invalide"}, 401"""
    order = request.get_json()
    total = 0.0
    order_details = []

    for item, quantity in order.items():
        quantity = int(quantity)
        if quantity > 0:
            price = ARTICLES.get(item, 0)
            subtotal = price * quantity
            total += subtotal
            order_details.append({"articles": item, 
                                    "quantity": quantity, 
                                    "unit_price": price, 
                                    "subtotal": subtotal,
                                    "total_price": subtotal})
            
            
        
        if total == 0:
            status = "empty"
        else:
            status = "ok"
    
    order_data = {"total": total, "order_details": order_details}
    save_order_data(order_data)

    return jsonify({"status": status,
                    "order_details": order_details}), 200