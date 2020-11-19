"""
Utils to authenticate with a set of cloud providers' container registries
(registry_auth) and Kubernetes clusters (cluster_auth) for use in
with-statements.

Current cloud providers supported: gcloud, aws, and azure.
"""
import json
import os
import subprocess
import shutil
import pathlib
import tempfile
import boto3

from hubploy.config import get_config
from contextlib import contextmanager

from ruamel.yaml import YAML
from ruamel.yaml.scanner import ScannerError
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
            elif provider == 'dockerconfig':
                yield from registry_auth_dockercfg(
                    deployment, **registry['dockerconfig']
                )
            else:
                raise ValueError(
                    f'Unknown provider {provider} found in hubploy.yaml')
    else:
        # We actually don't need to auth, but we are yielding anyway
        # contextlib.contextmanager does not like it when you don't yield
        yield

def registry_auth_dockercfg(deployment, filename):
    encrypted_file_path = os.path.join(
        'deployments', deployment, 'secrets', filename
    )

    orig_dockercfg = os.environ.get('DOCKER_CONFIG', None)
    with decrypt_file(encrypted_file_path) as auth_file_path:
        try:
            os.environ['DOCKER_CONFIG'] = auth_file_path
            yield
        finally:
            unset_env_var('DOCKER_CONFIG', orig_dockercfg)

def registry_auth_gcloud(deployment, project, service_key):
    """
    Setup GCR authentication with a service_key

    This changes *global machine state* on where docker can push to!
    """
    encrypted_service_key_path = os.path.join(
        'deployments', deployment, 'secrets', service_key
    )
    with decrypt_file(encrypted_service_key_path) as decrypted_service_key_path:
        subprocess.check_call([
            'gcloud', 'auth',
            'activate-service-account',
            '--key-file', os.path.abspath(decrypted_service_key_path)
        ])

    subprocess.check_call([
        'gcloud', 'auth', 'configure-docker'
    ])

    yield


@contextmanager
def _auth_aws(deployment, service_key=None, role_arn=None, role_session_name=None):
    """
    This helper contextmanager will update AWS_SHARED_CREDENTIALS_FILE if
    service_key is provided and AWS_SESSION_TOKEN if role_arn is provided.
    """
    # validate arguments
    if bool(service_key) == bool(role_arn):
        raise Exception("AWS authentication require either service_key or role_arn, but not both.")
    if role_arn:
        assert role_session_name, "always pass role_session_name along with role_arn"

    try:
        if service_key:
            original_credential_file_loc = os.environ.get("AWS_SHARED_CREDENTIALS_FILE", None)

            # Get path to service_key and validate its around
            service_key_path = os.path.join(
                'deployments', deployment, 'secrets', service_key
            )
            if not os.path.isfile(service_key_path):
                raise FileNotFoundError(
                    f'The service_key file {service_key_path} does not exist')

            os.environ["AWS_SHARED_CREDENTIALS_FILE"] = service_key_path

        elif role_arn:
            original_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID", None)
            original_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY", None)
            original_session_token = os.environ.get("AWS_SESSION_TOKEN", None)

            sts_client = boto3.client('sts')
            assumed_role_object = sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName=role_session_name
            )

            creds = assumed_role_object['Credentials']
            os.environ['AWS_ACCESS_KEY_ID'] = creds['AccessKeyId']
            os.environ['AWS_SECRET_ACCESS_KEY'] = creds['SecretAccessKey']
            os.environ['AWS_SESSION_TOKEN'] = creds['SessionToken']

        # return until context exits
        yield

    finally:
        if service_key:
            unset_env_var("AWS_SHARED_CREDENTIALS_FILE", original_credential_file_loc)
        elif role_arn:
            unset_env_var('AWS_ACCESS_KEY_ID', original_access_key_id)
            unset_env_var('AWS_SECRET_ACCESS_KEY', original_secret_access_key)
            unset_env_var('AWS_SESSION_TOKEN', original_session_token)


def registry_auth_aws(deployment, account_id, region, service_key=None, role_arn=None):
    """
    Setup AWS authentication to ECR container registry

    This changes *global machine state* on where docker can push to!
    """
    with _auth_aws(deployment, service_key=service_key, role_arn=role_arn, role_session_name="hubploy-registry-auth"):
        # FIXME: Use a temporary docker config
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

        registry = f'{account_id}.dkr.ecr.{region}.amazonaws.com'
        config.setdefault('credHelpers', {})[registry] = 'ecr-login'
        with open(docker_config, 'w') as f:
            json.dump(config, f)

        yield


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
        orig_kubeconfig = os.environ.get("KUBECONFIG", None)
        try:
            if provider == 'kubeconfig':
                encrypted_kubeconfig_path = os.path.join(
                    'deployments', deployment, 'secrets', cluster['kubeconfig']['filename']
                )
                with decrypt_file(encrypted_kubeconfig_path) as kubeconfig_path:
                    os.environ["KUBECONFIG"] = kubeconfig_path
                    yield
            else:

                # Temporarily kubeconfig file
                with tempfile.NamedTemporaryFile() as temp_kubeconfig:
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
    encrypted_service_key_path = os.path.join(
        'deployments', deployment, 'secrets', service_key
    )
    with decrypt_file(encrypted_service_key_path) as decrypted_service_key_path:
        subprocess.check_call([
            'gcloud', 'auth',
            'activate-service-account',
            '--key-file', os.path.abspath(decrypted_service_key_path)
        ])

    subprocess.check_call([
        'gcloud', 'container', 'clusters',
        f'--zone={zone}',
        f'--project={project}',
        'get-credentials', cluster
    ])

    yield


def cluster_auth_aws(deployment, account_id, cluster, region, service_key=None, role_arn=None):
    """
    Setup AWS authentication with service_key or with a role

    This changes *global machine state* on what current kubernetes cluster is!
    """
    with _auth_aws(deployment, service_key=service_key, role_arn=role_arn, role_session_name="hubploy-cluster-auth"):
        subprocess.check_call([
            'aws', 'eks', 'update-kubeconfig',
            '--name', cluster, '--region', region
        ])
        yield


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

    if env_var in os.environ:
        del os.environ[env_var]
    if (old_env_var_value is not None):
        os.environ[env_var] = old_env_var_value

@contextmanager
def decrypt_file(encrypted_path):
    """
    Provide secure temporary decrypted contents of a given file

    If file isn't a sops encrypted file, we assume no encryption is used
    and return the current path.
    """
    # We must first determine if the file is using sops
    # sops files are JSON/YAML with a `sops` key. So we first check
    # if the file is valid JSON/YAML, and then if it has a `sops` key
    with open(encrypted_path) as f:
        _, ext = os.path.splitext(encrypted_path)
        # Support the (clearly wrong) people who use .yml instead of .yaml
        if ext == '.yaml' or ext == '.yml':
            try:
                encrypted_data = yaml.load(f)
            except ScannerError:
                yield encrypted_path
                return
        elif ext == '.json':
            try:
                encrypted_data = json.load(f)
            except json.JSONDecodeError:
                yield encrypted_path
                return

    if 'sops' not in encrypted_data:
        yield encrypted_path
        return

    # If file has a `sops` key, we assume it's sops encrypted
    with tempfile.NamedTemporaryFile() as f:
        subprocess.check_call([
            'sops',
            '--output', f.name,
            '--decrypt', encrypted_path
        ])
        yield f.name
