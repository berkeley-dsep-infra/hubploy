import tempfile
import pathlib
import os
import secrets
import pytest
import subprocess
import docker


from hubploy import imagebuilder, gitutils


@pytest.fixture
def git_repo():
    """
    Fixture to create a git repo
    """
    with tempfile.TemporaryDirectory() as d:
        subprocess.check_output(['git', 'init'], cwd=d)
        yield pathlib.Path(d)


def test_imagebuild(git_repo):
    os.makedirs(git_repo / 'image')
    with open(git_repo / 'image/Dockerfile', 'w') as f:
        f.write('FROM busybox\n')
        f.write('ADD nonce /')

    nonce = secrets.token_hex(32)
    with open(git_repo / 'image/nonce', 'w') as f:
        f.write(nonce)
    
    subprocess.check_output(['git', 'add', '.'], cwd=git_repo)
    subprocess.check_output(['git', 'commit', '-m', 'test-commit'], cwd=git_repo)

    image_name = 'hubdeploy-test/' + secrets.token_hex(8)
    imagebuilder.ensure_image(str(git_repo / 'image'), image_name)

    expected_image_tag = gitutils.last_git_modified(str(git_repo / 'image'))
    expected_image_spec = f'{image_name}:{expected_image_tag}'

    client = docker.from_env()

    assert client.images.get(expected_image_spec) is not None

    assert client.containers.run(expected_image_spec, 'cat /nonce').decode() == nonce

    nonce_2 = secrets.token_hex(32)
    with open(git_repo / 'image/nonce', 'w') as f:
        f.write(nonce_2)
    
    subprocess.check_output(['git', 'add', '.'], cwd=git_repo)
    subprocess.check_output(['git', 'commit', '-m', 'test-commit-2'], cwd=git_repo)

    imagebuilder.ensure_image(str(git_repo / 'image'), image_name)

    expected_image_tag = gitutils.last_git_modified(str(git_repo / 'image'))
    expected_image_spec = f'{image_name}:{expected_image_tag}'

    assert client.images.get(expected_image_spec) is not None

    assert client.containers.run(expected_image_spec, 'cat /nonce').decode() == nonce_2