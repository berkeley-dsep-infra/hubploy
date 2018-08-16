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
    - config.yaml
"""
import itertools
import subprocess
from hubploy import gitutils
import os
import argparse
import shutil


def helm_upgrade(
    name,
    namespace,
    chart,
    config_files,
    config_overrides
):
    # Clear charts and do a helm dep up before installing
    # Clearing charts is important so we don't deploy charts that
    # have been removed from requirements.yaml
    # FIXME: verify if this is actually true
    shutil.rmtree(os.path.join(chart, 'charts'), ignore_errors=True)
    subprocess.check_call([
        'helm', 'dep', 'up'
    ], cwd=chart)

    cmd = [
        'helm',
        'upgrade',
        '--debug',
        '--wait',
        '--install',
        '--namespace', namespace,
        name, chart,
    ] 
    cmd += itertools.chain(*[['-f', cf] for cf in config_files]) 
    cmd += itertools.chain(*[['--set', f'{k}={v}'] for k, v in config_overrides.items()])
    subprocess.check_call(cmd)


def deploy(
    deployment,
    chart,
    environment,
    namespace=None,
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
        - config.yaml

    A docker image from deployments/{deployment}/image is expected to be
    already built and available with imagebuilder.
    `jupyterhub.singleuser.image.tag` will be automatically set to this image
    tag.
    """
    name = f'{deployment}-{environment}'

    if namespace is None:
        namespace = name
    config_files = [
        os.path.join('deployments', deployment, 'config.yaml'),
        os.path.join('deployments', deployment, 'secrets', f'{environment}.yaml'),
    ]

    image_tag = gitutils.last_git_modified(
        os.path.join('deployments', deployment, 'image')
    )

    # FIXME: Make this more configurable
    config_overrides = {
        'jupyterhub.singleuser.image.tag': image_tag
    }

    helm_upgrade(
        name,
        namespace,
        chart,
        config_files,
        config_overrides
    )


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        'deployment'
    )
    argparser.add_argument(
        'chart'
    )
    argparser.add_argument(
        'environment',
        choices=['staging', 'prod']
    )
    argparser.add_argument(
        '--namespace',
        default=None
    )

    args = argparser.parse_args()

    deploy(args.deployment, args.chart, args.environment, args.namespace)

if __name__ == '__main__':
    main()
