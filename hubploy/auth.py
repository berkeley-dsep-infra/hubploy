"""
Setup authentication from various providers
"""
import json
import os
import subprocess
import shutil

from hubploy.config import get_config

from ruamel.yaml import YAML
yaml = YAML(typ='rt')


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
        elif provider == 'azure':
            registry_auth_azure(
                deployment, **registry['azure']
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


def registry_auth_aws(deployment, project, zone, service_key):
    """
    Setup AWS authentication to ECR container registry

    This changes *global machine state* on where docker can push to!
    """
    service_key_path = os.path.join(
        'deployments', deployment, 'secrets', service_key
    )

    if not os.path.isfile(service_key_path):
        raise FileNotFoundError(
            f'The service_key file {service_key_path} does not exist')

    # move credentials to standard location
    cred_dir = os.path.expanduser('~/.aws')
    if not os.path.isdir(cred_dir):
        os.mkdir(cred_dir)
    shutil.copyfile(service_key_path, os.path.join(cred_dir, 'credentials'))

    registry = f'{project}.dkr.ecr.{zone}.amazonaws.com'
    # amazon-ecr-credential-helper installed in .circleci/config.yaml
    # this adds necessary line to authenticate docker with ecr
    docker_config_dir = os.path.expanduser('~/.docker')
    os.makedirs(docker_config_dir, exist_ok=True)
    docker_config = os.path.join(docker_config_dir, 'config.json')
    if os.path.exists(docker_config):
        with open(docker_config, 'r') as f:
            config = json.load(f)
    else:
        config = {'credHelpers': {}}
    config['credHelpers'][registry] = 'ecr-login'
    with open(docker_config, 'w') as f:
        json.dump(config, f)


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
        elif provider == 'azure':
            cluster_auth_azure(
                deployment, **cluster['azure']
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
    # move credentials to standard location
    service_key_path = os.path.join(
        'deployments', deployment, 'secrets', service_key
    )
    cred_dir = os.path.expanduser('~/.aws')
    if not os.path.isdir(cred_dir):
        os.mkdir(cred_dir)
    shutil.copyfile(service_key_path, os.path.join(cred_dir, 'credentials'))

    subprocess.check_call(['aws', 'eks', 'update-kubeconfig',
                           '--name', cluster, '--region', zone])


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




