"""
Setup authentication from various providers
"""
import json
import os
import shlex
import subprocess

from contextlib import contextmanager

from hubploy.config import get_config


def registry_auth(deployment):
    """
    Do appropriate registry authentication for given deployment
    """
    config = get_config(deployment)

    if 'images' in config and 'registry' in config['images']:
        registry = config['images']['registry']
        provider = registry.get('provider')
        if provider == 'gcloud':
            registry_auth_gcloud(
                deployment, **registry['gcloud']
            )
        elif provider == 'aws':
            registry_auth_aws(
                deployment, **registry['aws']
            )
        else:
            raise ValueError(
                f'Unknown provider {provider} found in hubploy.yaml')


def registry_auth_gcloud(deployment, project, service_key):
    """
    Setup GCR authentication with a service_key

    This changes *global machine state* on where docker can push to!
    """
    service_key_path = os.path.join(
        'deployments', deployment, 'secrets', service_key
    )
    subprocess.check_call([
        'gcloud', 'auth',
        'activate-service-account',
        '--key-file', os.path.abspath(service_key_path)
    ])

    subprocess.check_call([
        'gcloud', 'auth', 'configure-docker'
    ])


def registry_auth_aws(deployment, project, service_key):
    """
    Setup AWS authentication with a service_key

    This changes *global machine state* on where docker can push to!
    """

    service_key_path = os.path.abspath(os.path.join(
        'deployments', deployment, 'secrets', service_key))

    if not os.path.isfile(service_key_path):
        raise FileNotFoundError(
            f'The service_key file {service_key_path} does not exist')

    with local_env(AWS_SHARED_CREDENTIALS_FILE=service_key_path):
        cmd = subprocess.check_output(
            ['aws', 'ecr', 'get-login'],
            env=os.environ)
        # newer versions of aws cli have a '--no-include-email' option
        # this would mean we don't need to drop the -e none in the next line
        cmd = shlex.split(cmd.decode().strip().replace('-e none ', ''))
        subprocess.check_call(cmd, env=os.environ)


def cluster_auth(deployment):
    """
    Do appropriate cluster authentication for given deployment
    """
    config = get_config(deployment)

    if 'cluster' in config:
        cluster = config['cluster']
        provider = cluster.get('provider')
        if provider == 'gcloud':
            cluster_auth_gcloud(
                deployment, **cluster['gcloud']
            )
        elif provider == 'aws':
            cluster_auth_aws(
                deployment, **cluster['aws']
            )
        else:
            raise ValueError(
                f'Unknown provider {provider} found in hubploy.yaml')


def cluster_auth_gcloud(deployment, project, cluster, zone, service_key):
    """
    Setup GKE authentication with service_key

    This changes *global machine state* on what current kubernetes cluster is!
    """
    service_key_path = os.path.join(
        'deployments', deployment, 'secrets', service_key
    )
    subprocess.check_call([
        'gcloud', 'auth',
        'activate-service-account',
        '--key-file', os.path.abspath(service_key_path)
    ])

    subprocess.check_call([
        'gcloud', 'container', 'clusters',
        f'--zone={zone}',
        f'--project={project}',
        'get-credentials', cluster
    ])


def cluster_auth_aws(deployment, project, cluster, zone, service_key):
    """
    Setup AWS authentication with service_key

    This changes *global machine state* on what current kubernetes cluster is!
    """
    service_key_path = os.path.join(
        'deployments', deployment, 'secrets', service_key
    )

    if not os.path.isfile(service_key_path):
        raise FileNotFoundError(
            f'The service_key file {service_key_path} does not exist')

    with local_env(AWS_SHARED_CREDENTIALS_FILE=service_key_path):
        subprocess.check_call(['aws', 'eks', 'update-kubeconfig',
                               '--name', cluster], env=os.environ)


@contextmanager
def local_env(**kwargs):
    """
    Set environment variables as a context manager

    Original values are restored outside of the context manager
    """
    original_env = {key: os.getenv(key) for key in kwargs}
    try:
        os.environ.update(kwargs)
        yield
    finally:
        for key, value in original_env.items():
            if key is not None:
                os.environ[key] = value
            else:
                del os.environ[key]
