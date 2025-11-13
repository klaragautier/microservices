'''Crée l’objet Flask.
Importe les routes définies dans views.py.
Cette structure permet de séparer logique de l’application et exécution.'''

from flask import Flask
from .database import init_db
app= Flask(__name__)
init_db(app)
from app import views