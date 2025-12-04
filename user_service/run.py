# Ce fichier ne sert qu'au lancement du serveur web
# Il est possible de passer du mode debug au mode prod sans altérer le code de l'application

from app import app
from app.user import init_db

init_db()
app.run(host="0.0.0.0", port=5002, debug=True)