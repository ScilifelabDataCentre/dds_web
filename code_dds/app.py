"Web API for Data Delivery System"

# IMPORTS ########################################################### IMPORTS #

# Standard library

# Installed
# from flask_marshmallow import Marshmallow

# Own modules
from code_dds import create_app

# CONFIG ############################################################# CONFIG #

app = create_app()

# INITIATE ######################################################### INITIATE #

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
