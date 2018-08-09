"""
Builds docker images from directories when necessary
"""
import docker
from hubploy import gitutils, registry


def ensure_image(path, image_name):
    """
    Ensure latest image for dir path is built.
    """
    # Determine the image tag that should exist based on git
    # Check if the image tag *does* exist, from the registry
    # If it does not, build it and push it.
    last_commit = gitutils.last_git_modified(path)
    image_spec = f'{image_name}:{last_commit}'

    print(f'image spec is {image_spec}')
    image_manifest = registry.get_image_manifest(image_spec)
    print(image_manifest)
    if image_manifest is None:
        print(f'building image f{image_spec}')
        # Image that should exist does not, so let's build it
        build_image(path, image_spec)

def build_image(path, image_spec):
    """
    Build image at path and tag it with image_spec
    """
    client = docker.from_env()
    image = client.images.build(
        path=path,
        tag=image_spec,
        rm=True
    )
    print(image)


#ensure_image('deployments/datahub/image', 'yuvipanda/hubploy-test-datahub')