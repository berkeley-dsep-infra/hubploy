"""
Builds docker images from directories when necessary
"""
import docker
import argparse
import json
from hubploy import gitutils


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


def build_image(path, image_spec, build_progress_cb=None):
    """
    Build image at path and tag it with image_spec
    """
    api_client = docker.from_env().api
    build_output = api_client.build(
        path=path,
        tag=image_spec,
        rm=True,
        decode=True
    )
    for line in build_output:
        if build_progress_cb:
            build_progress_cb(line)


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        'path',
        help='Path to directory with dockerfile'
    )
    argparser.add_argument(
        'image_name',
        help='Name of image (including repository) to build, without tag'
    )

    def _print_progress(line):
        if 'stream' in line:
            print(line['stream'], end='')
        else:
            print(line)
    args = argparser.parse_args()


    if needs_building(args.path, args.image_name):
        print(f'Image {args.image_name} needs to be built...')
        # Determine the image_spec that needs to be built
        image_spec = make_imagespec(args.path, args.image_name)

        print(f'Starting to build {image_spec}')
        build_image(args.path, image_spec, _print_progress)

        print(f'Pushing {image_spec}')
        client = docker.from_env()

        repository, tag = image_spec.rsplit(':', 1)
        push_progress = client.images.push(repository, tag, decode=True)
        for l in push_progress:
            print(l)