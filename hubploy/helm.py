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

from hubploy.config import get_config


def helm_upgrade(
    name,
    namespace,
    chart,
    config_files,
    config_overrides,
    version,
    timeout,
    force
):
    # Clear charts and do a helm dep up before installing
    # Clearing charts is important so we don't deploy charts that
    # have been removed from requirements.yaml
    # FIXME: verify if this is actually true
    if os.path.exists(chart):
        shutil.rmtree(os.path.join(chart, 'charts'), ignore_errors=True)
        subprocess.check_call([
            'helm', 'dep', 'up'
        ], cwd=chart)

    cmd = [
        'helm',
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
    cmd += itertools.chain(*[['-f', cf] for cf in config_files])
    cmd += itertools.chain(*[['--set', v] for v in config_overrides])
    subprocess.check_call(cmd)


def deploy(
    deployment,
    chart,
    environment,
    namespace=None,
    helm_config_overrides=None,
    version=None,
    timeout=None,
    force=False
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
    if helm_config_overrides is None:
        helm_config_overrides = []

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
        helm_config_overrides.append(f'{image.helm_substitution_path}.tag={image.tag}')
        helm_config_overrides.append(f'{image.helm_substitution_path}.name={image.name}')

    helm_upgrade(
        name,
        namespace,
        chart,
        helm_config_files,
        helm_config_overrides,
        version,
        timeout,
        force
    )
