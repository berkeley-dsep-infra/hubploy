"""
Convention based helm deploys

Expects the following configuration layout from cwd:

chart-name/ (Helm deployment chart)
deployments/
  - deployment-name
    - secrets/
      - prod.yaml
      - staging.yaml
    - config/
      - common.yaml
      - staging.yaml
      - prod.yaml

Util to deploy a Helm chart (deploy) given hubploy configuration and Helm chart
configuration located in accordance to hubploy conventions.
"""

import itertools
import kubernetes.config
import logging
import os
import subprocess

from contextlib import ExitStack
from kubernetes.client import CoreV1Api, rest
from kubernetes.client.models import V1Namespace, V1ObjectMeta

from hubploy.config import get_config, validate_image_configs
from hubploy.auth import decrypt_file, cluster_auth, revert_gcloud_auth

from ruamel.yaml import YAML

logger = logging.getLogger(__name__)
yaml = YAML(typ="safe")
HELM_EXECUTABLE = os.environ.get("HELM_EXECUTABLE", "helm")


def helm_upgrade(
    name,
    namespace,
    context,
    chart,
    config_files,
    config_overrides_implicit,
    config_overrides_string,
    version,
    timeout,
    force,
    atomic,
    cleanup_on_fail,
    debug,
    verbose,
    helm_debug,
    dry_run,
):
    if verbose:
        logger.setLevel(logging.INFO)
    elif debug:
        logger.setLevel(logging.DEBUG)

    logger.info(f"Deploying {name} in namespace {namespace}")
    logger.debug(f"Running helm dep up in subdirectory '{chart}'")
    subprocess.check_call([HELM_EXECUTABLE, "dep", "up"], cwd=chart)

    # Create namespace explicitly, since helm3 removes support for it
    # See https://github.com/helm/helm/issues/6794
    # helm2 only creates the namespace if it doesn't exist, so we should be fine
    kubeconfig = os.environ.get("KUBECONFIG", None)
    logger.debug("Loading kubeconfig for k8s access")
    try:
        kubernetes.config.load_kube_config(config_file=kubeconfig, context=context)
        logger.info(f"Loaded kubeconfig {kubeconfig} for context {context}")
    except Exception as e:
        logger.info(
            f"Failed to load kubeconfig {kubeconfig} context {context} with "
            + f"exception:\n{e}\nTrying in-cluster config..."
        )
        kubernetes.config.load_incluster_config()
        logger.info("Loaded in-cluster kubeconfig")
    logger.debug(f"Checking for namespace {namespace} and creating if it doesn't exist")
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
        "upgrade",
        "--wait",
        "--install",
        "--namespace",
        namespace,
        name,
        chart,
    ]
    if context:
        cmd += ["--kube-context", context]
    if version:
        cmd += ["--version", version]
    if timeout:
        cmd += ["--timeout", timeout]
    if force:
        cmd += ["--force"]
    if atomic:
        cmd += ["--atomic"]
    if cleanup_on_fail:
        cmd += ["--cleanup-on-fail"]
    if helm_debug:
        cmd += ["--debug"]
    if dry_run:
        cmd += ["--dry-run"]
    cmd += itertools.chain(*[["-f", cf] for cf in config_files])
    cmd += itertools.chain(*[["--set", v] for v in config_overrides_implicit])
    cmd += itertools.chain(*[["--set-string", v] for v in config_overrides_string])

    logger.info(f"Running helm upgrade on {name}.")
    logger.debug("Helm upgrade command: " + " ".join(x for x in cmd))
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
    cleanup_on_fail=False,
    debug=False,
    verbose=False,
    helm_debug=False,
    dry_run=False,
):
    """
    Deploy a JupyterHub.

    Expects the following files to exist in current directory

    {chart}/ (Helm deployment chart)
    deployments/
    - {deployment}
        - secrets/
            - {environment}.yaml
        - config/
          - common.yaml
          - {environment}.yaml

    A docker image is expected to have already been built and tagged with
    "name" containing the full path to the repo, image name and tag.

    `jupyterhub.singleuser.image.tag` will be automatically set to this image
    tag.
    """
    if verbose:
        logger.setLevel(logging.INFO)
    elif debug:
        logger.setLevel(logging.DEBUG)

    logger.info(f"Deploying {deployment} to {environment}")

    if helm_config_overrides_implicit is None:
        helm_config_overrides_implicit = []
    if helm_config_overrides_string is None:
        helm_config_overrides_string = []

    logger.info(f"Getting image and deployment config for {deployment}")
    config = get_config(deployment, debug, verbose)
    name = f"{deployment}-{environment}"

    if namespace is None:
        namespace = name
    helm_config_files = [
        f
        for f in [
            os.path.join("deployments", deployment, "config", "common.yaml"),
            os.path.join("deployments", deployment, "config", f"{environment}.yaml"),
        ]
        if os.path.exists(f)
    ]
    logger.debug(f"Using helm config files: {helm_config_files}")

    helm_secret_files = [
        f
        for f in [
            # Support for secrets in same repo
            os.path.join("deployments", deployment, "secrets", f"{environment}.yaml"),
            # Support for secrets in a submodule repo
            os.path.join(
                "secrets", "deployments", deployment, "secrets", f"{environment}.yaml"
            ),
        ]
        if os.path.exists(f)
    ]
    logger.debug(f"Using helm secret files: {helm_secret_files}")

    validate_image_configs(helm_config_files)

    with ExitStack() as stack:
        # Use any specified kubeconfig context. A value of {namespace} will be
        # templated. A value of None will be interpreted as the current context.
        template_vars = dict(namespace=namespace)
        context = config.get("cluster", {}).get("kubeconfig", {}).get("context")
        if context:
            context = context.format(**template_vars)

        decrypted_secret_files = [
            stack.enter_context(decrypt_file(f)) for f in helm_secret_files
        ]

        # Just in time for k8s access, activate the cluster credentials
        logger.debug(
            "Activating cluster credentials for deployment "
            + f"{deployment} and performing deployment upgrade."
        )
        provider = config.get("cluster", {}).get("provider")
        if provider == "gcloud":
            current_login = stack.enter_context(
                cluster_auth(deployment, debug, verbose)
            )
        else:
            stack.enter_context(cluster_auth(deployment, debug, verbose))
        helm_upgrade(
            name,
            namespace,
            context,
            chart,
            helm_config_files + decrypted_secret_files,
            helm_config_overrides_implicit,
            helm_config_overrides_string,
            version,
            timeout,
            force,
            atomic,
            cleanup_on_fail,
            debug,
            verbose,
            helm_debug,
            dry_run,
        )
        # Revert the gcloud auth
        if provider == "gcloud":
            stack.enter_context(revert_gcloud_auth(current_login))
