"""
Builds docker images from directories when necessary
"""
import docker
import argparse
import json
from functools import partial
from hubploy import gitutils
from repo2docker.app import Repo2Docker


def make_imagespec(path, image_name):
    tag = gitutils.last_modified_commit(path)
    if not tag:
        tag = 'latest'
    return f'{image_name}:{tag}'


def build_image(client, path, image_spec, cache_from=None, push=False):
    builder = Repo2Docker()
    args = ['--subdir', path, '--image-name', image_spec,
            '--no-run', '--user-name', 'jovyan',
            '--user-id', '1000']
    if push:
        args.append('--push')
    args.append('.')
    builder.initialize(args)
    builder.start()


def pull_image(client, image_name, tag):
    """
    Pull given docker image
    """
    api_client = client.api
    pull_output = api_client.pull(
        image_name,
        tag,
        stream=True,
        decode=True
    )
    for line in pull_output:
        continue


def pull_images_for_cache(client, path, image_name, commit_range):
    # Pull last built image if we can
    cache_from = []
    # FIXME: cache_from doesn't work with repo2docker until https://github.com/jupyter/repo2docker/pull/478
    # is merged. So we just no-op this for now.
    return cache_from
    for i in range(2, 5):
        image = image_name
        # FIXME: Make this look for last modified since before beginning of commit_range
        tag = gitutils.last_modified_commit(path, n=i)
        try:
            print(f'Trying to pull {image}:{tag}')
            pull_image(client, image, tag)
            cache_from.append(f'{image}:{tag}')
            break
        except Exception as e:
            # Um, ignore if things fail!
            print(str(e))

def build_if_needed(client, path, image_name, commit_range, push=False):
    image_spec = make_imagespec(path, image_name)

    if (not commit_range) or gitutils.path_touched(path, commit_range=commit_range):
        print(f'Image {image_spec} needs to be built...')

        cache_from = pull_images_for_cache(client, path, image_name, commit_range)
        print(f'Starting to build {image_spec}')
        build_image(client, path, image_spec, cache_from, push)
        return True
    else:
        print(f'Image {image_spec}: already up to date')
        return False

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
        '--commit-range',
        help='Trigger image rebuilds only if path has changed in this commit range'
    )
    argparser.add_argument(
        '--push',
        action='store_true',
    )

    args = argparser.parse_args()

    client = docker.from_env()

    build_if_needed(client, args.path, args.image_name, args.commit_range, args.push)
