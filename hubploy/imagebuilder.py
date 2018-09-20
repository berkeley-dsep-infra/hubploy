"""
Builds docker images from directories when necessary
"""
import docker
import argparse
import json
from functools import partial
from hubploy import gitutils


def make_imagespec(path, image_name, last=1):
    last_commit = gitutils.last_git_modified(path, last)
    return f'{image_name}:{last_commit}'


def needs_building(client, path, image_name):
    """
    Return true if image in path needs building
    """
    return True
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


def build_image(client, path, image_spec, cache_from=None, build_progress_cb=None):
    """
    Build image at path and tag it with image_spec
    """
    api_client = client.api
    build_output = api_client.build(
        path=path,
        tag=image_spec,
        rm=True,
        decode=True,
        cache_from=cache_from
    )
    for line in build_output:
        if build_progress_cb:
            build_progress_cb(line)
        if 'error' in line:
            raise ValueError('Build failed')


def build_repo2docker(client, path, image_spec):
    ENTRYPOINT = '''\
#!/bin/bash
cp -ra /srv/home/ -T ${HOME}
if [ -x binder/start ]; then
  exec binder/start "$@"
else
  exec "$@"
fi
'''
    NEWLINE = '\n'
    ESCAPED_NEWLINE = '\\n'
    APPENDIX = f'''
USER root
RUN rm -rf .npm .cache && cp -ra ${{HOME}} /srv/home
RUN printf '{ENTRYPOINT.replace(NEWLINE, ESCAPED_NEWLINE)}' > /entrypoint.sh && chmod +x /entrypoint.sh

USER ${{NB_USER}}
ENTRYPOINT ["/entrypoint.sh"]
'''
    from repo2docker.app import Repo2Docker
    builder = Repo2Docker()
    builder.initialize(['--subdir', path, '--image-name', image_spec,
                        '--no-run',
                        '--user-name', 'jovyan',
                        '--user-id', '1000',
                        '--appendix', APPENDIX,
                        '.',])
    builder.start()


def pull_image(client, image_name, tag, pull_progress_cb):
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
        if pull_progress_cb:
            pull_progress_cb(line)

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
    argparser.add_argument(
        '--repo2docker',
        action='store_true',
        help='Build using repo2docker',
    )

    def _print_progress(key, line):
        if key in line:
            # FIXME: end='' doesn't seem to work?
            print(line[key].rstrip())
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

        # Pull last built image if we can
        cache_from = []
        for i in range(2, 5):
            image = args.image_name
            tag = gitutils.last_git_modified(args.path, i)
            try:
                print(f'Trying to pull {image}:{tag}')
                pull_image(client, image, tag, partial(_print_progress, 'progress'))
                cache_from.append(f'{image}:{tag}')
            except Exception as e:
                # Um, ignore if things fail!
                print(str(e))

        print(f'Starting to build {image_spec}')
        if args.repo2docker:
            build_repo2docker(client, args.path, image_spec)
        else:
            build_image(client, args.path, image_spec, cache_from, partial(_print_progress, 'stream'))

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
