import socket
import tempfile
import pathlib
import os
import secrets
import pytest
import subprocess
import docker
import time


from hubploy import imagebuilder, gitutils


@pytest.fixture
def git_repo():
    """
    Fixture to create a git repo
    """
    with tempfile.TemporaryDirectory() as d:
        subprocess.check_output(['git', 'init'], cwd=d)
        yield d

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

def commit_nonce(git_repo):
    """
    Commit a nonce file in given git repo

    Return nonce value used
    """
    nonce = secrets.token_hex(32)
    with open(os.path.join(git_repo, 'image/nonce'), 'w') as f:
        f.write(nonce)

    subprocess.check_output(['git', 'add', '.'], cwd=git_repo)
    subprocess.check_output(['git', 'commit', '-m', 'test-commit'], cwd=git_repo)

    return nonce

def test_imagebuild(git_repo, local_registry):
    """
    End to end test of image building.
    """
    client = docker.from_env()
    image_name = f'{local_registry}/hubdeploy-test/' + secrets.token_hex(8)
    image_dir = os.path.join(git_repo, 'image')

    # Set up image directory & Dockerfile
    os.makedirs(image_dir)
    with open(os.path.join(image_dir, 'Dockerfile'), 'w') as f:
        f.write('FROM busybox\n')
        f.write('ADD nonce /')

    # Round 1
    # Make a commit with a random nonce in git repository
    nonce_1 = commit_nonce(git_repo)

    # We haven't build this image so far, so it must need building
    assert imagebuilder.needs_building(client, image_dir, image_name)

    # Build the image
    imagebuilder.build_image(client, image_dir, imagebuilder.make_imagespec(image_dir, image_name))

    # Validate that the image we expect to be built / tagged is
    expected_image_tag_1 = gitutils.last_git_modified(image_dir)
    expected_image_spec_1 = f'{image_name}:{expected_image_tag_1}'
    assert client.images.get(expected_image_spec_1) is not None

    # Validate that the image being built is actually what we wanted
    assert client.containers.run(expected_image_spec_1, 'cat /nonce').decode() == nonce_1

    # Push the image, and verify that we now know we don't need to build it
    assert imagebuilder.needs_building(client, image_dir, image_name)
    client.images.push(expected_image_spec_1)
    assert not imagebuilder.needs_building(client, image_dir, image_name)

    # Round 2! We do this to make sure we handle rebuilding properly
    # Make a commit with a new random nonce in git repository
    nonce_2 = commit_nonce(git_repo)

    # We haven't built the image since this commit, so it must need building
    assert imagebuilder.needs_building(client, image_dir, image_name)

    # Build the image
    imagebuilder.build_image(client, image_dir, imagebuilder.make_imagespec(image_dir, image_name))

    # Validate that the image we expect to be built / tagged is
    expected_image_tag_2 = gitutils.last_git_modified(image_dir)
    expected_image_spec_2 = f'{image_name}:{expected_image_tag_2}'
    assert client.images.get(expected_image_spec_2) is not None

    # Validate that the image being built is actually what we wanted
    assert client.containers.run(expected_image_spec_2, 'cat /nonce').decode() == nonce_2

    # Push the image, and verify that we now know we don't need to build it anymore
    assert imagebuilder.needs_building(client, image_dir, image_name)
    client.images.push(expected_image_spec_2)
    assert not imagebuilder.needs_building(client, image_dir, image_name)


def test_build_fail(git_repo):
    """
    Throw an error if the build fails
    """
    client = docker.from_env()
    with open(os.path.join(git_repo, 'Dockerfile'), 'w') as f:
        f.write('FROM busybox\n')
        f.write('RUN non-existent')
    with pytest.raises(ValueError):
        imagebuilder.build_image(client, git_repo, 'test:latest')
