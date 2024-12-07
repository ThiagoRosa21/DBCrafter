from flask import Flask

app = Flask(__name__)

#Rotas 

from views import *

if __name__ == "__main__":
    app.run()
    
        