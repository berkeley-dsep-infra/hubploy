"""
Utils for dealing with hubploy config
"""
import os
from ruamel.yaml import YAML
yaml = YAML(typ='rt')

def get_config(deployment):
    """
    Return configuration if it exists for a deployment
    """
    config_path = os.path.abspath(os.path.join('deployments', deployment, 'hubploy.yaml'))
    if not os.path.exists(config_path):
        return {}
    
    with open(config_path) as f:
        config = yaml.load(f)
    
    return config
    