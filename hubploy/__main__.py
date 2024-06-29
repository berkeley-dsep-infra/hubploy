import argparse
import logging
import sys
import textwrap

logging.basicConfig(stream=sys.stdout, level=logging.WARNING)
logger = logging.getLogger(__name__)

import hubploy
from hubploy import helm

from argparse import RawTextHelpFormatter

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
        "deployment"
    )
    deploy_parser.add_argument(
        "chart"
    )
    deploy_parser.add_argument(
        "environment",
        choices=["develop", "staging", "prod"]
    )
    deploy_parser.add_argument(
        "--namespace",
        default=None
    )
    deploy_parser.add_argument(
        "--set",
        action="append",
    )
    deploy_parser.add_argument(
        "--set-string",
        action="append",
    )
    deploy_parser.add_argument(
        "--version",
    )
    deploy_parser.add_argument(
        "--timeout"
    )
    deploy_parser.add_argument(
        "--force",
        action="store_true"
    )
    deploy_parser.add_argument(
        "--atomic",
        action="store_true"
    )
    deploy_parser.add_argument(
        "--cleanup-on-fail",
        action="store_true"
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
        help=textwrap.dedent("""\
        Override one or more images and tags to deploy. Format is:\n
        <path_to_image1/image_name>:<tag1> <path_to_image2/image_name>:<tag2> ...\n \n
        IMPORTANT: The order of images passed in must match the order in which
        they appear in hubploy.yaml and separated by spaces without quotes. You
        must always specify a tag when overriding images.
        """)
    )

    args = argparser.parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)
    elif args.debug:
        logger.setLevel(logging.DEBUG)
    logger.info(args)

    # Attempt to load the config early, fail if it doesn't exist or is invalid
    try:
        config = hubploy.config.get_config(
            args.deployment,
            debug=False,
            verbose=False
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

