# Ce fichier ne sert qu'au lancement du serveur web
# Il est possible de passer du mode debug au mode prod sans altérer le code de l'application

# On ajoute le 0.0.0.0 avec Docker pour que le conteneur soit accessible depuis l'extérieur
from app import app
app.run(host="0.0.0.0", port=5000, debug=True)