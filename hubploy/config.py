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


def validate_image_configs(config_files):
    """
    Check the given config files for any image references. If any are found,
    ensure that the image name and tag are present. If not, raise an error
    and exit.
    """
    image_counter = len(config_files)
    for config_file in config_files:
        logger.debug(f"Checking config file for image references: {config_file}")
        with open(config_file) as f:
            config = yaml.load(f)
            if not config:
                continue

        image_name_in_file = (
            config.get("jupyterhub", {})
            .get("singleuser", {})
            .get("image", {})
            .get("name", None)
        )
        image_tag_in_file = (
            config.get("jupyterhub", {})
            .get("singleuser", {})
            .get("image", {})
            .get("tag", None)
        )

        if image_name_in_file:
            if not image_tag_in_file:
                raise RuntimeError(
                    f"Error: image name '{image_name_in_file}' in {config_file} has no tag specified."
                )
        elif not image_name_in_file:
            image_counter -= 1
            continue
        else:
            continue

    if image_counter == 0:
        raise RuntimeError(f"No image references found in config files: {config_files}")
    else:
        logger.info(
            f"Found {image_counter} valid image reference(s) in config files: {config_files}"
        )


def get_config(deployment, debug=False, verbose=False):
    """
    Returns hubploy.yaml configuration as a Python dictionary if it exists for
    a given deployment. This contains the auth and cluster deployment information.
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
