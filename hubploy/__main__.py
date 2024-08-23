import argparse
import hubploy
import logging
import os
import sys
import textwrap

from hubploy import helm
from argparse import RawTextHelpFormatter

logging.basicConfig(stream=sys.stdout, level=logging.WARNING)
logger = logging.getLogger(__name__)

def main():
    argparser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
    subparsers = argparser.add_subparsers(dest="command")

    argparser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable tool debug output (not including helm debug)."
    )
    argparser.add_argument(
        "-D",
        "--helm-debug",
        action="store_true",
        help="Enable Helm debug output."
    )
    argparser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output."
    )

    deploy_parser = subparsers.add_parser(
        "deploy",
        help="Deploy a chart to the given environment."
    )

    deploy_parser.add_argument(
        "deployment",
        help="The name of the hub to deploy."
    )
    deploy_parser.add_argument(
        "chart",
        help="The path to the main hub chart."
    )
    deploy_parser.add_argument(
        "environment",
        choices=["develop", "staging", "prod"],
        help="The environment to deploy to."
    )
    deploy_parser.add_argument(
        "--namespace",
        default=None,
        help="Helm option: the namespace to deploy to. If not specified, " +
        "the namespace will be derived from the environment argument."
    )
    deploy_parser.add_argument(
        "--set",
        action="append",
        help="Helm option:  set values on the command line (can specify " +
        "multiple or separate values with commas: key1=val1,key2=val2)"
    )
    deploy_parser.add_argument(
        "--set-string",
        action="append",
        help="Helm option: set STRING values on the command line (can " +
        "specify multiple or separate values with commas: key1=val1,key2=val2)"
    )
    deploy_parser.add_argument(
        "--version",
        help="Helm option: specify a version constraint for the chart " +
        "version to use. This constraint can be a specific tag (e.g. 1.1.1) " +
        "or it may reference a valid range (e.g. ^2.0.0). If this is not " +
        "specified, the latest version is used."
    )
    deploy_parser.add_argument(
        "--timeout",
        help="Helm option: time in seconds to wait for any individual " +
        "Kubernetes operation (like Jobs for hooks, etc).  Defaults to 300 " +
        "seconds."
    )
    deploy_parser.add_argument(
        "--force",
        action="store_true",
        help="Helm option: force resource updates through a replacement strategy."
    )
    deploy_parser.add_argument(
        "--atomic",
        action="store_true",
        help="Helm option: if set, upgrade process rolls back changes made " +
        "in case of failed upgrade. The --wait flag will be set automatically " +
        "if --atomic is used."
    )
    deploy_parser.add_argument(
        "--cleanup-on-fail",
        action="store_true",
        help="Helm option: allow deletion of new resources created in this " +
        "upgrade when upgrade fails."
    )
    deploy_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run the helm upgrade command. This also renders the " +
        "chart to STDOUT."
    )
    deploy_parser.add_argument(
        "--image-overrides",
        nargs="+",
        help=textwrap.dedent(
            """\
        Override one or more images and tags to deploy. Format is:\n
        <path_to_image1/image_name>:<tag1> <path_to_image2/image_name>:<tag2> ...\n \n
        IMPORTANT: The order of images passed in must match the order in which
        they appear in hubploy.yaml and separated by spaces without quotes. You
        must always specify a tag when overriding images.
        """
        )
    )

    args = argparser.parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)
    elif args.debug:
        logger.setLevel(logging.DEBUG)
    logger.info(args)

    is_on_ci = os.environ.get("CI", False)
    if is_on_ci:
        if args.helm_debug or args.dry_run:
            print("--helm-debug and --dry-run are not allowed to be used in a CI environment.")
            print("Exiting...")
            sys.exit(1)

    # Attempt to load the config early, fail if it doesn't exist or is invalid
    try:
        config = hubploy.config.get_config(
            args.deployment,
            debug=False,
            verbose=False
        )
        if not config:
            raise hubploy.config.DeploymentNotFoundError(
                "Deployment '{}' not found in hubploy.yaml".format(args.deployment)
            )
    except hubploy.config.DeploymentNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    helm.deploy(
        args.deployment,
        args.chart,
        args.environment,
        args.namespace,
        args.set,
        args.set_string,
        args.version,
        args.timeout,
        args.force,
        args.atomic,
        args.cleanup_on_fail,
        args.debug,
        args.verbose,
        args.helm_debug,
        args.dry_run,
        args.image_overrides
    )

if __name__ == "__main__":
    main()

