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


class RemoteImage:
    """
    A simple class to represent a remote image
    """

    def __init__(
        self, name, tag=None, helm_substitution_path="jupyterhub.singleuser.image"
    ):
        """
        Define an Image from the hubploy config

        name: Fully qualified name of image
        tag: Tag of image (github hash)
        helm_substitution_path: Dot separated path in a helm file that should
                                be populated with this image spec
        """
        # name must not be empty
        # FIXME: Validate name to conform to docker image name guidelines
        if not name or name.strip() == "":
            raise ValueError(
                "Name of image to be built is not specified. Check "
                + "hubploy.yaml of your deployment"
            )
        self.name = name
        self.tag = tag
        self.helm_substitution_path = helm_substitution_path

        if self.tag is None:
            self.image_spec = f"{self.name}"
        else:
            self.image_spec = f"{self.name}:{self.tag}"


def get_config(deployment, debug=False, verbose=False):
    """
    Returns hubploy.yaml configuration as a Python dictionary if it exists for
    a given deployment, and also augments it with a set of RemoteImage objects
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

    if "images" in config:
        images_config = config["images"]

        # A single image is being deployed
        if "image_name" in images_config:
            if ":" in images_config["image_name"]:
                image_name, tag = images_config["image_name"].split(":")
                images = [{"name": image_name, "tag": tag}]
            else:
                images = [{"name": images_config["image_name"]}]

        else:
            # Multiple images are being deployed
            image_list = images_config["images"]
            images = []
            for i in image_list:
                if ":" in i["name"]:
                    image_name, tag = i["name"].split(":")
                    logger.info(f"Tag for {image_name}: {tag}")
                    images.append(
                        {
                            "name": image_name,
                            "tag": tag,
                        }
                    )
                else:
                    images.append({"name": i["name"]})

        config["images"]["images"] = [RemoteImage(**i) for i in images]

        # Backwards compatibility checker for cluster block
        if (
            config["cluster"]["provider"] == "aws"
            and "project" in config["cluster"]["aws"]
        ):
            config["cluster"]["aws"]["account_id"] = config["cluster"]["aws"]["project"]
            del config["cluster"]["aws"]["project"]

        if (
            config["cluster"]["provider"] == "aws"
            and "zone" in config["cluster"]["aws"]
        ):
            config["cluster"]["aws"]["region"] = config["cluster"]["aws"]["zone"]
            del config["cluster"]["aws"]["zone"]

    logger.debug(f"Config loaded and parsed: {config}")
    return config
