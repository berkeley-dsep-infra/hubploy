"""
Builds docker images from directories when necessary
"""
import docker
import json
from hubploy import gitutils, registry

def make_imagespec(path, image_name):
    last_commit = gitutils.last_git_modified(path)
    return f'{image_name}:{last_commit}'

def needs_building(path, image_name):
    """
    Return true if image in path needs building
    """
    image_spec = make_imagespec(path, image_name)
    client = docker.from_env()
    try:
        image_manifest = client.images.get_registry_data(image_spec)
        return image_manifest is None
    except docker.errors.ImageNotFound:
        return True
    except docker.errors.APIError as e:
        if e.explanation == 'manifest unknown: manifest unknown':
            return True
        else:
            raise

def ensure_image(path, image_name, build_progress_cb=None):
    """
    Ensure latest image for dir path is built.
    """
    image_spec = make_imagespec(path, image_name)

    # Determine the image tag that should exist based on git
    # Check if the image tag *does* exist, from the registry
    # If it does not, build it and push it.
    if needs_building(path, image_name):
        # Image that should exist does not, so let's build it
        build_image(path, image_spec, build_progress_cb)

def build_image(path, image_spec, build_progress_cb):
    """
    Build image at path and tag it with image_spec
    """
    client = docker.from_env()
    _, build_output = client.images.build(
        path=path,
        tag=image_spec,
        rm=True
    )
    for line in build_output:
        if build_progress_cb:
            build_progress_cb(line)


#ensure_image('deployments/datahub/image', 'yuvipanda/hubploy-test-datahub')