"""
Convention based helm deploys

Expects the following configuration layout from cwd:

chart-name/ (Helm deployment chart)
deployments/
  - deployment-name
    - image/
    - secrets/
      - prod.yaml
      - staging.yaml
    - config/
      - common.yaml
      - staging.yaml
      - prod.yaml
"""
import itertools
import os
import shutil
import subprocess
import kubernetes.config
from kubernetes.client import CoreV1Api, rest
from kubernetes.client.models import V1Namespace, V1ObjectMeta

from hubploy.config import get_config


HELM_EXECUTABLE = os.environ.get('HELM_EXECUTABLE', 'helm')


def helm_upgrade(
    name,
    namespace,
    chart,
    config_files,
    config_overrides_implicit,
    config_overrides_string,
    version,
    timeout,
    force,
    atomic,
    cleanup_on_fail
):
    # Clear charts and do a helm dep up before installing
    # Clearing charts is important so we don't deploy charts that
    # have been removed from requirements.yaml
    # FIXME: verify if this is actually true
    if os.path.exists(chart):
        shutil.rmtree(os.path.join(chart, 'charts'), ignore_errors=True)
        subprocess.check_call([
            HELM_EXECUTABLE, 'dep', 'up'
        ], cwd=chart)

    # Create namespace explicitly, since helm3 removes support for it
    # See https://github.com/helm/helm/issues/6794
    # helm2 only creates the namespace if it doesn't exist, so we should be fine
    kubeconfig = os.environ.get("KUBECONFIG", None)

    try:
        kubernetes.config.load_kube_config(config_file=kubeconfig)
    except:
        kubernetes.config.load_incluster_config()

    api = CoreV1Api()
    try:
        api.read_namespace(namespace)
    except rest.ApiException as e:
        if e.status == 404:
            # Create namespace
            print(f"Namespace {namespace} does not exist, creating it...")
            api.create_namespace(V1Namespace(metadata=V1ObjectMeta(name=namespace)))
        else:
            raise

    cmd = [
        HELM_EXECUTABLE,
        'upgrade',
        '--wait',
        '--install',
        '--namespace', namespace,
        name, chart,
    ]
    if version:
        cmd += ['--version', version]
    if timeout:
        cmd += ['--timeout', timeout]
    if force:
        cmd += ['--force']
    if atomic:
        cmd += ['--atomic']
    if cleanup_on_fail:
        cmd += ['--cleanup-on-fail']
    cmd += itertools.chain(*[['-f', cf] for cf in config_files])
    cmd += itertools.chain(*[['--set', v] for v in config_overrides_implicit])
    cmd += itertools.chain(*[['--set-string', v] for v in config_overrides_string])
    subprocess.check_call(cmd)


def deploy(
    deployment,
    chart,
    environment,
    namespace=None,
    helm_config_overrides_implicit=None,
    helm_config_overrides_string=None,
    version=None,
    timeout=None,
    force=False,
    atomic=False,
    cleanup_on_fail=False
):
    """
    Deploy a JupyterHub.

    Expects the following files to exist in current directory

    {chart}/ (Helm deployment chart)
    deployments/
    - {deployment}
        - image/
        - secrets/
            - {environment}.yaml
        - config/
          - common.yaml
          - {environment}.yaml

    A docker image from deployments/{deployment}/image is expected to be
    already built and available with imagebuilder.
    `jupyterhub.singleuser.image.tag` will be automatically set to this image
    tag.
    """
    if helm_config_overrides_implicit is None:
        helm_config_overrides_implicit = []
    if helm_config_overrides_string is None:
        helm_config_overrides_string = []

    config = get_config(deployment)

    name = f'{deployment}-{environment}'

    if namespace is None:
        namespace = name
    helm_config_files = [f for f in [
        os.path.join('deployments', deployment, 'config', 'common.yaml'),
        os.path.join('deployments', deployment, 'config', f'{environment}.yaml'),
        os.path.join('deployments', deployment, 'secrets', f'{environment}.yaml'),
    ] if os.path.exists(f)]

    for image in config['images']['images']:
        # We can support other charts that wrap z2jh by allowing various
        # config paths where we set image tags and names.
        # We default to one sublevel, but we can do multiple levels.
        # With the PANGEO chart, we this could be set to `pangeo.jupyterhub.singleuser.image`
        helm_config_overrides_string.append(f'{image.helm_substitution_path}.tag={image.tag}')
        helm_config_overrides_string.append(f'{image.helm_substitution_path}.name={image.name}')

    helm_upgrade(
        name,
        namespace,
        chart,
        helm_config_files,
        helm_config_overrides_implicit,
        helm_config_overrides_string,
        version,
        timeout,
        force,
        atomic,
        cleanup_on_fail,
    )
