#!/usr/bin/env python

import yaml
import os

def parse_config(yaml_path = None):
    """
    Parse given yaml file or try to find yaml file in know location
    """
    config = {}
    yaml_lookup_locations = [os.getcwd(), os.path.expanduser("~"), os.path.join(os.path.expanduser("~"), ".config")]
    if not yaml_path or not os.path.exists(yaml_path):
        for yloc in yaml_lookup_locations:
            ypath = os.path.join(yloc, "dportal.yaml")
            if os.path.exists(ypath):
                yaml_path = ypath
                break
    
    if yaml_path:
        with open(yaml_path, "r") as yfile:
            config = yaml.load(yfile)
    
    return config
