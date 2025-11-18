# gateway/gateway.py
# Rôle : afficher le site HTML et appeler les microservices en HTTP.


from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
import json


gateway_app=Flask(__name__)

# --- Adresses des microservices ---
USER_SERVICE_URL = "http://localhost:5001"
AUTH_SERVICE_URL = "http://localhost:5002"
ORDERS_SERVICE_URL = "http://localhost:5003"

@gateway_app.route("/")
def index():
    return jsonify({"message": "API Gateway is running"}), 200



### PAGE 1 - Login ###
@gateway_app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template("/login.html")

### PAGE 2 - ACCUEIL ###
@gateway_app.route('/accueil') 
def accueil():
    user = request.args.get('user', 'Invité')
    error_message = request.args.get('error_message')
    return render_template('accueil.html', user=user, error_message=error_message)


### PAGE 3 - ACHAT ###
@gateway_app.route('/achat')
def achat():
    status_message = request.args.get('status', 'pending')
    current_user = request.args.get('user', 'Invité')
    grand_total = request.args.get("total", "0")
    order_details_json = request.args.get('details', '[]')
    try:
        order_details = json.loads(order_details_json)
    except json.JSONDecodeError:
        order_details = []

    grand_total = request.args.get('total', type=float)
    if grand_total is None:
        grand_total = round(sum(i.get('total_price', 0) for i in order_details), 2)

    return render_template('achat.html',
                           status=status_message,
                           user=current_user,
                           order_details=order_details,
                           grand_total=grand_total)


# --- Route /login qui appelle auth_service ---
@gateway_app.route("/api/login", methods=["POST"])
def api_login():
    r = requests.post(f"{AUTH_SERVICE_URL}/login", data=request.json)
    data = r.json()

    if r.status_code == 200:
        return jsonify({"redirect": url_for("accueil", user=data["user"])})

    return jsonify({"error": data.get("error", "Erreur inconnue")}), 400



# --- Route /user qui appelle user_service ---
@gateway_app.route("/api/user/<username>")
def api_user(username):
    r = requests.get(f"{USER_SERVICE_URL}/users/{username}")
    return jsonify(r.json()), r.status_code



# --- Route /ordres qui appelle oders_service ---
@gateway_app.route("/api/orders/<username>")
def api_orders(username):
    r = requests.get(f"{ORDERS_SERVICE_URL}/orders/{username}")
    return jsonify(r.json()), r.status_code

@gateway_app.route("/api/submit_order/<user>", methods=["POST"])
def api_submit_order(user):
    r = requests.post(
        f"{ORDERS_SERVICE_URL}/submit_order/{user}", 
        data=request.form    # envoie directement les quantités du formulaire
    )
    data = r.json()

    return jsonify({"redirect": data["redirect_url"]})

