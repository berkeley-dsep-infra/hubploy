"""
A util (get_config) that process hubploy.yaml deployment configuration and
returns it embedded with a set of LocalImage objects with filesystem paths made
absolute.
"""

import logging
import os
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)
yaml = YAML(typ="safe")


class DeploymentNotFoundError(Exception):
    def __init__(self, deployment, path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.deployment = deployment
        self.path = path

    def __str__(self):
        return f"deployment {self.deployment} not found at {self.path}"


def get_config(deployment, debug=False, verbose=False):
    """
    Returns hubploy.yaml configuration as a Python dictionary if it exists for
    a given deployment, and also augments it with a set of LocalImage objects
    in ["images"]["images"].
    """
    if verbose:
        logger.setLevel(logging.INFO)
    elif debug:
        logger.setLevel(logging.DEBUG)

    deployment_path = os.path.abspath(os.path.join("deployments", deployment))
    if not os.path.exists(deployment_path):
        raise DeploymentNotFoundError(deployment, deployment_path)

    config_path = os.path.join(deployment_path, "hubploy.yaml")
    logger.info(f"Loading hubploy config from {config_path}")
    with open(config_path) as f:
        # If config_path isn't found, this will raise a FileNotFoundError with
        # useful info
        config = yaml.load(f)

    logger.debug(f"Config loaded and parsed: {config}")
    return config
