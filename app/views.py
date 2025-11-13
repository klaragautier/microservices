from app import app
from flask import render_template, request, redirect, url_for
import random
import json
import datetime
import os
import jwt
import secrets  
from .database import add_user, get_user_by_username, check_password


# --- Configuration pour les JWT ---
app.config['SECRET_KEY'] = 'secret123' 
ACCESS_TOKEN_EXPIRES_MINUTES = 15
REFRESH_TOKEN_EXPIRES_DAYS = 7


# --- Configuration des fichiers de données ---
ORDERS_FILE = 'orders.json' # Fichier pour les commandes

# --- Fichier pour stocker les refresh tokens (façon "base") ---
REFRESH_TOKENS_FILE = 'refresh_tokens.json'


# --- Catalogue des produits (Pour validation et calcul des prix) ---
PRODUCTS = {
    "Fraises": 2.50,
    "Haricots": 1.80,
    "Laine": 12.00,
    "Peches": 3.00,
    "Pasteques": 7.00,
    "Pates": 1.20
}

# --- Données initiales par défaut (utilisées si les fichiers n'existent pas) ---
# On laisse vide car l'utilisateur doit créer son compte
DEFAULT_USERS = {} 
DEFAULT_ORDERS = {}
DEFAULT_REFRESH_TOKENS = {}

# --- Fonctions de gestion des fichiers JSON ---

def load_data(filename):
    """Charge les données depuis un fichier JSON donné."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Retourne un dictionnaire vide si non trouvé
        return {} 
    except json.JSONDecodeError:
        # Retourne un dictionnaire vide si corrompu
        return {}

def save_data(data, filename):
    """Sauvegarde les données dans un fichier JSON donné."""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


# --- Helpers refresh token ---

def create_access_token(username: str):
    """Crée un JWT d'accès de courte durée pour un utilisateur."""
    now = datetime.datetime.utcnow()
    payload = {
        "sub": username,  # sujet = l'utilisateur
        "iat": now,
        "exp": now + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRES_MINUTES)
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm="HS256")
    # PyJWT >= 2 retourne déjà une str, sinon tu peux faire token.decode("utf-8")
    return token

def add_refresh_token(username: str, token: str, expires_at: datetime.datetime):
    """Enregistre un refresh token pour un utilisateur dans refresh_tokens.json."""
    data = load_data(REFRESH_TOKENS_FILE)
    if username not in data:
        data[username] = []
    data[username].append({
        "token": token,
        "expires_at": expires_at.isoformat(),
        "revoked": False
    })
    save_data(data, REFRESH_TOKENS_FILE)


def create_refresh_token(username: str) -> str:
    """Crée un refresh token aléatoire de longue durée et le stocke dans le JSON."""
    token = secrets.token_urlsafe(64)  # grande chaîne aléatoire
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=REFRESH_TOKEN_EXPIRES_DAYS)
    add_refresh_token(username, token, expires_at)
    return token

def find_refresh_token(token: str):
    """Recherche un refresh token exact dans refresh_tokens.json."""
    data = load_data(REFRESH_TOKENS_FILE)
    for user, tokens in data.items():
        for entry in tokens:
            if entry["token"] == token:
                return user, entry
    return None, None


def revoke_refresh_token(token: str):
    """Marque un refresh token comme révoqué dans refresh_tokens.json."""
    data = load_data(REFRESH_TOKENS_FILE)
    for user, tokens in data.items():
        for entry in tokens:
            if entry["token"] == token:
                entry["revoked"] = True
                save_data(data, REFRESH_TOKENS_FILE)
                return True
    return False

# --- Fonction : Initialisation des fichiers au démarrage ---
def initialize_files():
    """Crée les fichiers JSON s'ils n'existent pas avec les données par défaut."""
    
    # 1. Initialisation de orders.json
    if not os.path.exists(ORDERS_FILE):
        print(f"Création initiale de {ORDERS_FILE}...")
        save_data(DEFAULT_ORDERS, ORDERS_FILE)

    # 2. Initialisation de refresh_tokens.json vide si besoin
    if not os.path.exists(REFRESH_TOKENS_FILE):
        print(f"Création initiale de {REFRESH_TOKENS_FILE}...")
        save_data(DEFAULT_REFRESH_TOKENS, REFRESH_TOKENS_FILE)

# --- Exécuter l'initialisation au chargement du module ---
initialize_files()


### PAGE 1 - LOGIN / INSCRIPTION (MISE À JOUR) ###
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('user')
        password = request.form.get('password')
        action = request.form.get('action') 
        
        # 1. Tenter de récupérer l'utilisateur dans la DB
        db_user = get_user_by_username(user)

        if action == 'register':
            # --- LOGIQUE D'INSCRIPTION ---
            if db_user:
                # Utilisateur déjà existant
                return render_template('login.html', error="Ce nom d'utilisateur existe déjà. Veuillez vous connecter.")
            
            # Création du nouveau compte dans SQLite avec mot de passe haché
            if add_user(user, password):
                # Génération des tokens après inscription
                access_token = create_access_token(user)
                refresh_token = create_refresh_token(user)

                resp = redirect(url_for('accueil', user=user))
                # Access token : durée courte, utilisé pour accéder à l'appli
                resp.set_cookie(
                    'access_token',
                    access_token,
                    httponly=True,
                    samesite='Lax'
                )
                # Refresh token : durée longue, pour redemander un nouveau access token
                resp.set_cookie(
                    'refresh_token',
                    refresh_token,
                    httponly=True,
                    samesite='Strict'
                )
                return resp
            else:
                return render_template('login.html', error="Erreur lors de la création du compte.")

        # --- LOGIQUE DE CONNEXION ---
        if db_user:
            # L'utilisateur existe, vérification du mot de passe haché
            # db_user['password_hash'] contient le hash stocké
            if check_password(db_user['password_hash'], password):
                # Génération des tokens après connexion
                access_token = create_access_token(user)
                refresh_token = create_refresh_token(user)

                resp = redirect(url_for('accueil', user=user))
                resp.set_cookie(
                    'access_token',
                    access_token,
                    httponly=True,
                    samesite='Lax'
                )
                resp.set_cookie(
                    'refresh_token',
                    refresh_token,
                    httponly=True,
                    samesite='Strict'
                )
                return resp
            else:
                return render_template('login.html', error="Nom d'utilisateur ou mot de passe incorrect.")
        else:
            return render_template('login.html', error="Nom d'utilisateur ou mot de passe incorrect.")

            
    # Requête GET (affichage du formulaire)
    return render_template('login.html', error=request.args.get('error'))


### PAGE 2 - ACCUEIL (Liste des articles / Panier) ###
@app.route('/accueil') 
def accueil():
    user = request.args.get('user', 'Invité')
    error_message = request.args.get('error_message')
    return render_template('accueil.html', user=user, error_message=error_message)


### PAGE 3 - CONFIRMATION ACHAT ###
@app.route('/achat')
def achat():
    status_message = request.args.get('status', 'pending')
    current_user = request.args.get('user', 'Invité')

    order_details_json = request.args.get('details', '[]')
    try:
        order_details = json.loads(order_details_json)
    except json.JSONDecodeError:
        order_details = []

    # 👉 conversion directe en float si présent
    grand_total = request.args.get('total', type=float)
    if grand_total is None:
        grand_total = round(sum(i.get('total_price', 0) for i in order_details), 2)

    return render_template('achat.html',
                           status=status_message,
                           user=current_user,
                           order_details=order_details,
                           grand_total=grand_total)


### Tockens

@app.route('/refresh', methods=['POST'])
def refresh_token():
    """Renouvelle le access token grâce au refresh token."""
    refresh_token = request.cookies.get('refresh_token')

    if not refresh_token:
        return {"error": "Refresh token manquant"}, 401

    # 1️⃣ Chercher le token dans la base JSON
    username, token_entry = find_refresh_token(refresh_token)

    if not token_entry:
        return {"error": "Refresh token inconnu"}, 401

    # 2️⃣ Vérifier s'il est révoqué
    if token_entry.get("revoked", False):
        return {"error": "Refresh token révoqué"}, 401

    # 3️⃣ Vérifier expiration
    expires_at = datetime.datetime.fromisoformat(token_entry["expires_at"])
    if datetime.datetime.utcnow() > expires_at:
        return {"error": "Refresh token expiré"}, 401

    # 4️⃣ ROTATION : révoquer l'ancien refresh token
    revoke_refresh_token(refresh_token)

    # 5️⃣ Générer un nouveau access token
    new_access = create_access_token(username)

    # 6️⃣ Générer un nouveau refresh token (rotation recommandée)
    new_refresh = create_refresh_token(username)

    # 7️⃣ Réponse avec les nouveaux cookies
    resp = {
        "message": "Nouveau access token généré",
        "user": username
    }

    response = app.response_class(
        response=json.dumps(resp),
        status=200,
        mimetype='application/json'
    )

    # cookie access token
    response.set_cookie(
        'access_token',
        new_access,
        httponly=True,
        samesite='Lax'
    )

    # cookie refresh token
    response.set_cookie(
        'refresh_token',
        new_refresh,
        httponly=True,
        samesite='Strict'
    )

    return response



# --- ROUTE : Soumission du panier (POST) ---
@app.route('/submit_order/<user>', methods=['POST'])
def submit_order(user):
    cart_items = []
    has_items = False
    
    # 1. Récupérer les quantités du formulaire
    for item_name, unit_price in PRODUCTS.items():
        try:
            quantity = int(request.form.get(item_name, 0))
        except ValueError:
            quantity = 0 
            
        if quantity > 0:
            cart_items.append({
                "article": item_name,
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": round(quantity * unit_price, 2)
            })
            has_items = True

    # 2. Validation du panier
    if not has_items:
        return redirect(url_for('accueil', 
                                user=user, 
                                error_message="Votre panier est vide. Veuillez sélectionner au moins un article."))
        
    # 3. Lancer la logique de paiement
    return process_payment(user, cart_items)


# --- FONCTION : Traite le paiement et l'enregistrement (accepte la liste d'articles) ---
def process_payment(user, cart_items):
    total_amount = round(sum(item['total_price'] for item in cart_items), 2)
    
    # Simuler un succès 1 fois sur 2
    if random.random() < 0.5:
        # PAIEMENT RÉUSSI (et Enregistrement)
        
        try:
            orders_data = load_data(ORDERS_FILE)
            
            if user not in orders_data:
                 orders_data[user] = []
            
            # Créer la nouvelle commande (objet complexe)
            new_order = {
                "order_id": str(datetime.datetime.now().timestamp()).replace('.', ''), 
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total": total_amount,
                "items": cart_items 
            }
            
            orders_data[user].append(new_order)
            save_data(orders_data, ORDERS_FILE)
            
            status = 'ok'
            
        except Exception as e:
            print(f"Erreur d'enregistrement JSON: {e}")
            status = 'error'
        
    else:
        # PAIEMENT ÉCHOUÉ (Simulé)
        status = 'error'

    # Redirection vers la page de confirmation (achat)
    return redirect(url_for(
        'achat',
        status=status,
        user=user,
        total=f"{total_amount:.2f}",
        details=json.dumps(cart_items, separators=(',', ':'), ensure_ascii=False)
))