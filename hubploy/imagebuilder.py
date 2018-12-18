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
    r2d = Repo2Docker()
    args = ['--subdir', path, '--image-name', image_spec,
            '--no-run', '--user-name', 'jovyan',
            '--user-id', '1000']
    if cache_from:
        for cf in cache_from:
            args += ['--cache-from', cf]

    if push:
        args.append('--push')

    args.append('.')

    r2d.initialize(args)
    r2d.start()


def pull_image(client, image_name, tag):
    """
    Pull given docker image
    """
    pull_output = client.api.pull(
        image_name,
        tag,
        stream=True,
        decode=True
    )
    for line in pull_output:
        pass


def pull_images_for_cache(client, path, image_name, commit_range):
    # Pull last built image if we can
    cache_from = []
    for i in range(1, 5):
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

    return cache_from

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