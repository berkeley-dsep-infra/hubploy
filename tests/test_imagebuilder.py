import socket
import tempfile
import contextlib
import pathlib
import os
import secrets
import pytest
import subprocess
import docker
import pathlib
import time
import docker.errors

from hubploy import config, gitutils


@pytest.fixture
def git_repo():
    """
    Fixture to create a git repo
    """
    with tempfile.TemporaryDirectory() as d:
        subprocess.check_output(['git', 'init'], cwd=d)
        yield pathlib.Path(d)

def git(repo_dir, *cmd):
    with cwd(repo_dir):
        subprocess.check_call(['git'] + list(cmd))

@pytest.fixture
def open_port():
    """
    Fixture providing an open port on the host system
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("",0))
        return s.getsockname()[1]
    finally:
        s.close()


@pytest.fixture
def local_registry(open_port):
    """
    Fixture to create a local docker registry
    """
    if 'DOCKER_REGISTRY' in os.environ:
        # We are running in CI, where we already have a local registry
        yield os.environ['DOCKER_REGISTRY']
        return
    client = docker.from_env()
    container = client.containers.run(
        'registry:2',
        detach=True,
        ports={'5000/tcp': open_port}
    )
    time.sleep(2)
    try:
        yield f'localhost:{open_port}'
    finally:
        container.stop()
        container.remove()

@contextlib.contextmanager
def cwd(new_dir):
    curdir = os.getcwd()
    try:
        os.chdir(new_dir)
        yield
    finally:
        os.chdir(curdir)


def commit_file(repo_dir, path, contents):
    full_path = repo_dir / path
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    with open(full_path, 'w') as f:
        f.write(contents)

    git(repo_dir, 'add', path)
    git(repo_dir, 'commit', '-m', f'Added {path}')

def test_tag_generation(git_repo):
    """
    Tag should be last commit of modified image dir
    """
    commit_file(git_repo, 'image/Dockerfile', 'FROM busybox')
    commit_file(git_repo, 'unrelated/file', 'unrelated')

    with cwd(git_repo):
        image = config.LocalImage('test-image', 'image')
        assert image.tag == gitutils.last_modified_commit('image')
        # Make sure tag isn't influenced by changes outside of iamge dir
        assert image.tag != gitutils.last_modified_commit('unrelated')


        # Change the Dockerfile and see what's up
        commit_file(git_repo, 'image/Dockerfile', 'FROM busybox:latest')
        new_image = config.LocalImage('test-image', 'image')
        assert new_image.tag == gitutils.last_modified_commit('image')
        assert new_image.tag != image.tag

        # Test that our older commit is listed as a 'possible parent' tag
        assert image.tag in new_image.get_possible_parent_tags()

def test_build_image(git_repo, local_registry):
    """
    Test building a small image, pushing it and testing it exists
    """
    commit_file(git_repo, 'image/Dockerfile', 'FROM busybox')

    with cwd(git_repo):
        image = config.LocalImage(f'{local_registry}/test-build-image', 'image')
        image.build()

        assert not image.exists_in_registry()

        image.push()

        assert image.exists_in_registry()

