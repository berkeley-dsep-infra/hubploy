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


def needs_building(client, path, image_name):
    """
    Return true if image in path needs building
    """
    image_spec = make_imagespec(path, image_name)
    try:
        image_manifest = client.images.get_registry_data(image_spec)
        return image_manifest is None
    except docker.errors.ImageNotFound:
        return True
    except docker.errors.APIError as e:
        # This message seems to vary across registries?
        if e.explanation.startswith('manifest unknown: '):
            return True
        else:
            raise


def build_image(client, path, image_spec, build_progress_cb=None):
    """
    Build image at path and tag it with image_spec
    """
    api_client = client.api
    build_output = api_client.build(
        path=path,
        tag=image_spec,
        rm=True,
        decode=True
    )
    for line in build_output:
        if build_progress_cb:
            build_progress_cb(line)
        if 'error' in line:
            raise ValueError('Build failed')


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
    argparser.add_argument(
        '--registry-url',
        help='URL of docker registry to talk to'
    )
    # FIXME: Don't do this?
    argparser.add_argument(
        '--registry-password',
        help='Docker registry password'
    )
    argparser.add_argument(
        '--registry-username',
        help='Docker registry username'
    )
    argparser.add_argument(
        '--push',
        action='store_true',
    )

    def _print_progress(line):
        if 'stream' in line:
            # FIXME: end='' doesn't seem to work?
            print(line['stream'].rstrip())
        else:
            print(line)
    args = argparser.parse_args()

    client = docker.from_env()
    if args.registry_url:
        client.login(
            username=args.registry_username,
            password=args.registry_password,
            registry=args.registry_url
        )

    # Determine the image_spec that needs to be built
    image_spec = make_imagespec(args.path, args.image_name)

    if needs_building(client, args.path, args.image_name):
        print(f'Image {args.image_name} needs to be built...')

        print(f'Starting to build {image_spec}')
        build_image(client, args.path, image_spec, _print_progress)


        if args.push:
            print(f'Pushing {image_spec}')
            repository, tag = image_spec.rsplit(':', 1)
            push_progress = client.images.push(repository, tag, decode=True, stream=True)
            for l in push_progress:
                # FIXME: Nicer output here
                print(l)
                if 'error' in l:
                    raise ValueError('Pushing failed')
    else:
        print(f'Image {image_spec}: already up to date')