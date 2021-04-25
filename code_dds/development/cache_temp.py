""" Temparoy methods for cacheing """

import os
import json
from flask import current_app

tmp_ucache_path = os.path.join(current_app.config.get("LOCAL_TEMP_CACHE"), "{}_cache.json")

def store_temp_ucache(tu, tp):
    with open(tmp_ucache_path.format(tu), "w") as tchf:
        json.dump({"username": tu, "password": tp}, tchf)
    
def clear_temp_ucache(tu):
    if os.path.exists(tmp_ucache_path.format(tu)):
        os.remove(tmp_ucache_path.format(tu))
