# Il s'agit du point d'entrée de l'application
# Le dossier est devenu un package

# On importe la classe Flask
# On initialise l'application Flask 
# __name__ permet à Flask de savoir ou il se trouve 


from flask import Flask
app=Flask(__name__)

app.config["SECRET_KEY"] = "secret123"

# On importe le fichier user.py où se trouveront les routes
from app import user