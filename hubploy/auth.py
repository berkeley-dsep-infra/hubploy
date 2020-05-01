"""
Setup authentication from various providers
"""
import json
import os
import subprocess
import shutil
import tempfile

from hubploy.config import get_config
from contextlib import contextmanager

from ruamel.yaml import YAML
yaml = YAML(typ='rt')


@contextmanager
def registry_auth(deployment, push, check_registry):
    """
    Do appropriate registry authentication for given deployment
    """

    if push or check_registry:

        config = get_config(deployment)

        if 'images' in config and 'registry' in config['images']:
            registry = config['images']['registry']
            provider = registry.get('provider')
            if provider == 'gcloud':
                yield from registry_auth_gcloud(
                    deployment, **registry['gcloud']
                )
            elif provider == 'aws':
                yield from registry_auth_aws(
                    deployment, **registry['aws']
                )
            elif provider == 'azure':
                yield from registry_auth_azure(
                    deployment, **registry['azure']
                )
            else:
                raise ValueError(
                    f'Unknown provider {provider} found in hubploy.yaml')
    else:
        # We actually don't need to auth, but we are yielding anyway
        # contextlib.contextmanager does not like it when you don't yield
        yield

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

    yield


def registry_auth_aws(deployment, project, zone, service_key=None, role=None):
    """
    Setup AWS authentication to ECR container registry

    This changes *global machine state* on where docker can push to!
    """

    if not service_key and not role:
        raise Exception('AWS authentication requires either a service key or the use of a role')

    registry = f'{project}.dkr.ecr.{zone}.amazonaws.com'

    try:
        if service_key:
            # Get credentials from standard location
            service_key_path = os.path.join(
                'deployments', deployment, 'secrets', service_key
            )

            if not os.path.isfile(service_key_path):
                raise FileNotFoundError(
                    f'The service_key file {service_key_path} does not exist')

            original_credential_file_loc = os.environ.get("AWS_SHARED_CREDENTIALS_FILE", None)

            # Set env variable for credential file location
            os.environ["AWS_SHARED_CREDENTIALS_FILE"] = service_key_path

            # TODO: fix this comment
            # Requires amazon-ecr-credential-helper to already be installed
            # this adds necessary line to authenticate docker with ecr
            docker_config_dir = os.path.expanduser('~/.docker')
            os.makedirs(docker_config_dir, exist_ok=True)
            docker_config = os.path.join(docker_config_dir, 'config.json')
            if os.path.exists(docker_config):
                with open(docker_config, 'r') as f:
                    config = json.load(f)
            else:
                config = {}

            config.setdefault('credHelpers', {})[registry] = 'ecr-login'
            with open(docker_config, 'w') as f:
                json.dump(config, f)

        if role:
            subprocess.check_call([
                'aws', 'sts', 'assume-role',
                f'--role-arn={role}',
                '--role-session-name=docker'
            ])

        yield

    finally:
        if service_key:
            # Unset env variable for credential file location
            unset_env_var("AWS_SHARED_CREDENTIALS_FILE", original_credential_file_loc)

        if role:
            pass
            # drop perms here???


def registry_auth_azure(deployment, resource_group, registry, auth_file):
    """
    Azure authentication for ACR

    In hubploy.yaml include:

    registry:
      provider: azure
      azure:
        resource_group: resource_group_name
        registry: registry_name
        auth_file: azure_auth_file.yaml

    The azure_service_principal.json file should have the following
    keys: appId, tenant, password. This is the format produced
    by the az command when creating a service principal.
    See https://docs.microsoft.com/en-us/azure/aks/kubernetes-service-principal
    """

    # parse Azure auth file
    auth_file_path = os.path.join('deployments', deployment, 'secrets', auth_file)
    with open(auth_file_path) as f:
        auth = yaml.load(f)

    # log in
    subprocess.check_call([
        'az', 'login', '--service-principal',
        '--user', auth['appId'],
        '--tenant', auth['tenant'],
        '--password', auth['password']
    ])

    # log in to ACR
    subprocess.check_call([
        'az', 'acr', 'login',
        '--name', registry
    ])

    yield


@contextmanager
def cluster_auth(deployment):
    """
    Do appropriate cluster authentication for given deployment
    """
    config = get_config(deployment)

    if 'cluster' in config:
        cluster = config['cluster']
        provider = cluster.get('provider')

        # Temporarily kubeconfig file
        temp_kubeconfig = tempfile.NamedTemporaryFile()
        orig_kubeconfig = os.environ.get("KUBECONFIG", None)

        try:
            os.environ["KUBECONFIG"] = temp_kubeconfig.name

            if provider == 'gcloud':
                yield from cluster_auth_gcloud(
                    deployment, **cluster['gcloud']
                )
            elif provider == 'aws':
                yield from cluster_auth_aws(
                    deployment, **cluster['aws']
                )
            elif provider == 'azure':
                yield from cluster_auth_azure(
                    deployment, **cluster['azure']
                )
            else:
                raise ValueError(
                    f'Unknown provider {provider} found in hubploy.yaml')
        finally:
            unset_env_var("KUBECONFIG", orig_kubeconfig)


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

    yield


def cluster_auth_aws(deployment, project, cluster, zone, service_key=None, role=None):
    """
    Setup AWS authentication with service_key

    This changes *global machine state* on what current kubernetes cluster is!
    """

    if not service_key and not role:
        raise Exception('AWS authentication requires either a service key or the use of a role')

    def update_kubeconfig():
        subprocess.check_call([
        'aws', 'eks', 'update-kubeconfig',
        '--name', cluster, '--region', zone
    ])

    try:
        if service_key:
            # Get credentials from standard location
            service_key_path = os.path.join(
                'deployments', deployment, 'secrets', service_key
            )

            original_credential_file_loc = os.environ.get("AWS_SHARED_CREDENTIALS_FILE", None)

            # Set env variable for credential file location
            os.environ["AWS_SHARED_CREDENTIALS_FILE"] = service_key_path

            update_kubeconfig()

        if role:
            subprocess.check_call([
                'aws', 'sts', 'assume-role',
                f'--role-arn={role}',
                '--role-session-name=cluster'
            ])

            update_kubeconfig()

        yield

    finally:
        if service_role:
            # Unset env variable for credential file location
            unset_env_var("AWS_SHARED_CREDENTIALS_FILE", original_credential_file_loc)

        if role:
            pass
            # drop perms here???


def cluster_auth_azure(deployment, resource_group, cluster, auth_file):
    """

    Azure authentication for AKS

    In hubploy.yaml include:

    cluster:
      provider: azure
      azure:
        resource_group: resource_group_name
        cluster: cluster_name
        auth_file: azure_auth_file.yaml

    The azure_service_principal.json file should have the following
    keys: appId, tenant, password. This is the format produced
    by the az command when creating a service principal.
    """

    # parse Azure auth file
    auth_file_path = os.path.join('deployments', deployment, 'secrets', auth_file)
    with open(auth_file_path) as f:
        auth = yaml.load(f)

    # log in
    subprocess.check_call([
        'az', 'login', '--service-principal',
        '--user', auth['appId'],
        '--tenant', auth['tenant'],
        '--password', auth['password']
    ])

    # get cluster credentials
    subprocess.check_call([
        'az', 'aks', 'get-credentials',
        '--name', cluster,
        '--resource-group', resource_group
    ])

    yield

def unset_env_var(env_var, old_env_var_value):
    """
    If the old environment variable's value exists, replace the current one with the old one
    If the old environment variable's value does not exist, delete the current one
    """

    del os.environ[env_var]
    if (old_env_var_value is not None):
        os.environ[env_var] = old_env_var_value

