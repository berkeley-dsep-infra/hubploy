"""
Utils to authenticate with a set of cloud providers' container registries
(registry_auth) and Kubernetes clusters (cluster_auth) for use in
with-statements.

Current cloud providers supported: gcloud, aws, and azure.
"""

import boto3
import json
import logging
import os
import subprocess
import tempfile

from contextlib import contextmanager
from hubploy.config import get_config
from ruamel.yaml import YAML
from ruamel.yaml.scanner import ScannerError

logger = logging.getLogger(__name__)
yaml = YAML(typ="rt")


@contextmanager
def cluster_auth(deployment, debug=False, verbose=False):
    """
    Do appropriate cluster authentication for given deployment
    """
    if verbose:
        logger.setLevel(logging.INFO)
    elif debug:
        logger.setLevel(logging.DEBUG)

    logger.info(f"Getting auth config for {deployment}")
    config = get_config(deployment, debug, verbose)

    if "cluster" in config:
        cluster = config["cluster"]
        provider = cluster.get("provider")
        orig_kubeconfig = os.environ.get("KUBECONFIG", None)

        try:
            if provider == "kubeconfig":
                logger.info(
                    f"Attempting to authenticate to {cluster} with "
                    + "existing kubeconfig."
                )
                logger.debug(
                    "Using kubeconfig file "
                    + f"deploylemts/{deployment}/secrets/{cluster['kubeconfig']['filename']}"
                )
                encrypted_kubeconfig_path = os.path.join(
                    "deployments",
                    deployment,
                    "secrets",
                    cluster["kubeconfig"]["filename"],
                )
                with decrypt_file(encrypted_kubeconfig_path) as kubeconfig_path:
                    os.environ["KUBECONFIG"] = kubeconfig_path
                    yield
            else:
                # Temporarily kubeconfig file
                with tempfile.NamedTemporaryFile() as temp_kubeconfig:
                    os.environ["KUBECONFIG"] = temp_kubeconfig.name
                    logger.info(f"Attempting to authenticate with {provider}...")

                    if provider == "gcloud":
                        yield from cluster_auth_gcloud(deployment, **cluster["gcloud"])
                    elif provider == "aws":
                        yield from cluster_auth_aws(deployment, **cluster["aws"])
                    elif provider == "azure":
                        yield from cluster_auth_azure(deployment, **cluster["azure"])
                    else:
                        raise ValueError(
                            f"Unknown provider {provider} found in " + "hubploy.yaml"
                        )
        finally:
            unset_env_var("KUBECONFIG", orig_kubeconfig)


def cluster_auth_gcloud(deployment, project, cluster, zone, service_key):
    """
    Setup GKE authentication with service_key

    This changes *global machine state* on what current kubernetes cluster is!
    """
    current_login_command = [
        "gcloud",
        "config",
        "get-value",
        "account",
    ]
    logger.info("Saving current gcloud login")
    logger.debug(
        "Running gcloud command: " + " ".join(x for x in current_login_command)
    )
    current_login = subprocess.check_output(current_login_command).decode("utf-8").strip()
    logger.info(f"Current gcloud login: {current_login}")

    encrypted_service_key_path = os.path.join(
        "deployments", deployment, "secrets", service_key
    )
    with decrypt_file(encrypted_service_key_path) as decrypted_service_key_path:
        gcloud_auth_command = [
            "gcloud",
            "auth",
            "activate-service-account",
            "--key-file",
            os.path.abspath(decrypted_service_key_path),
        ]
        logger.info(f"Activating service account for {project}")
        logger.debug(
            "Running gcloud command: " + " ".join(x for x in gcloud_auth_command)
        )
        subprocess.check_call(gcloud_auth_command)

    gcloud_cluster_credential_command = [
        "gcloud",
        "container",
        "clusters",
        f"--zone={zone}",
        f"--project={project}",
        "get-credentials",
        cluster,
    ]
    logger.info(f"Getting credentials for {cluster} in {zone}")
    logger.debug(
        "Running gcloud command: "
        + " ".join(x for x in gcloud_cluster_credential_command)
    )
    subprocess.check_call(gcloud_cluster_credential_command)

    yield current_login

@contextmanager
def revert_gcloud_auth(current_login):
    """
    Revert gcloud authentication to previous state
    """
    if current_login:
        logger.info(f"Reverting gcloud login to {current_login}")
        subprocess.check_call(
            ["gcloud", "config", "set", "account", current_login]
        )
    else:
        logger.info("Reverting gcloud login to default")
        subprocess.check_call(["gcloud", "config", "unset", "account"])
    yield

@contextmanager
def _auth_aws(deployment, service_key=None, role_arn=None, role_session_name=None):
    """
    This helper contextmanager will update AWS_SHARED_CREDENTIALS_FILE if
    service_key is provided and AWS_SESSION_TOKEN if role_arn is provided.
    """
    # validate arguments
    if bool(service_key) == bool(role_arn):
        raise Exception(
            "AWS authentication require either service_key or role_arn, but not both."
        )
    if role_arn:
        assert role_session_name, "always pass role_session_name along with role_arn"

    try:
        original_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID", None)
        original_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY", None)
        original_session_token = os.environ.get("AWS_SESSION_TOKEN", None)
        if service_key:
            original_credential_file_loc = os.environ.get(
                "AWS_SHARED_CREDENTIALS_FILE", None
            )

            # Get path to service_key and validate its around
            encrypted_service_key_path = os.path.join(
                "deployments", deployment, "secrets", service_key
            )
            if not os.path.isfile(encrypted_service_key_path):
                raise FileNotFoundError(
                    f"The service_key file {encrypted_service_key_path} does not exist"
                )

            logger.info(f"Decrypting service key {encrypted_service_key_path}")
            with decrypt_file(encrypted_service_key_path) as decrypted_service_key_path:
                auth = yaml.load(open(decrypted_service_key_path))
                os.environ["AWS_ACCESS_KEY_ID"] = auth["creds"]["aws_access_key_id"]
                os.environ["AWS_SECRET_ACCESS_KEY"] = auth["creds"][
                    "aws_secret_access_key"
                ]
            logger.info("Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")

        elif role_arn:
            original_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID", None)
            original_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY", None)
            original_session_token = os.environ.get("AWS_SESSION_TOKEN", None)

            sts_client = boto3.client("sts")
            assumed_role_object = sts_client.assume_role(
                RoleArn=role_arn, RoleSessionName=role_session_name
            )

            creds = assumed_role_object["Credentials"]
            os.environ["AWS_ACCESS_KEY_ID"] = creds["AccessKeyId"]
            os.environ["AWS_SECRET_ACCESS_KEY"] = creds["SecretAccessKey"]
            os.environ["AWS_SESSION_TOKEN"] = creds["SessionToken"]

        # return until context exits
        yield

    finally:
        if service_key:
            unset_env_var("AWS_SHARED_CREDENTIALS_FILE", original_credential_file_loc)
            unset_env_var("AWS_ACCESS_KEY_ID", original_access_key_id)
            unset_env_var("AWS_SECRET_ACCESS_KEY", original_secret_access_key)
            unset_env_var("AWS_SESSION_TOKEN", original_session_token)
        elif role_arn:
            unset_env_var("AWS_ACCESS_KEY_ID", original_access_key_id)
            unset_env_var("AWS_SECRET_ACCESS_KEY", original_secret_access_key)
            unset_env_var("AWS_SESSION_TOKEN", original_session_token)


def cluster_auth_aws(deployment, cluster, region, service_key=None, role_arn=None):
    """
    Setup AWS authentication with service_key or with a role

    This changes *global machine state* on what current kubernetes cluster is!
    """
    with _auth_aws(
        deployment,
        service_key=service_key,
        role_arn=role_arn,
        role_session_name="hubploy-cluster-auth",
    ):
        subprocess.check_call(
            ["aws", "eks", "update-kubeconfig", "--name", cluster, "--region", region],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT
        )
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

    The azure_service_principal.json file should have the following keys:
    appId, tenant, password.

    This is the format produced by the az command when creating a service
    principal.
    """

    # parse Azure auth file
    auth_file_path = os.path.join("deployments", deployment, "secrets", auth_file)
    with open(auth_file_path) as f:
        auth = yaml.load(f)

    # log in
    subprocess.check_call(
        [
            "az",
            "login",
            "--service-principal",
            "--user",
            auth["appId"],
            "--tenant",
            auth["tenant"],
            "--password",
            auth["password"],
        ]
    )

    # get cluster credentials
    subprocess.check_call(
        [
            "az",
            "aks",
            "get-credentials",
            "--name",
            cluster,
            "--resource-group",
            resource_group,
        ]
    )

    yield


def unset_env_var(env_var, old_env_var_value):
    """
    If the old environment variable's value exists, replace the current one
    with the old one.

    If the old environment variable's value does not exist, delete the current
    one.
    """

    if env_var in os.environ:
        del os.environ[env_var]
    if old_env_var_value is not None:
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
    logger.info(f"Decrypting {encrypted_path}")
    with open(encrypted_path) as f:
        _, ext = os.path.splitext(encrypted_path)
        # Support the (clearly wrong) people who use .yml instead of .yaml
        if ext == ".yaml" or ext == ".yml":
            try:
                encrypted_data = yaml.load(f)
            except ScannerError:
                yield encrypted_path
                return
        elif ext == ".json":
            try:
                encrypted_data = json.load(f)
            except json.JSONDecodeError:
                yield encrypted_path
                return
        elif ext == ".cfg":
            try:
                with open(encrypted_path) as f:
                    encrypted_data = f.read()
            except Exception:
                yield encrypted_path
                return

    if "sops" not in encrypted_data:
        logger.info("File is not sops encrypted, returning path")
        yield encrypted_path
        return

    else:
        # If file has a `sops` key, we assume it's sops encrypted
        sops_command = ["sops", "--decrypt", encrypted_path]

        logger.info("File is sops encrypted, decrypting...")
        logger.debug(
            "Executing: "
            + " ".join(sops_command)
            + " (with output to a temporary file)"
        )
        with tempfile.NamedTemporaryFile() as f:
            subprocess.check_call(
                ["sops", "--output", f.name, "--decrypt", encrypted_path]
            )
            yield f.name
