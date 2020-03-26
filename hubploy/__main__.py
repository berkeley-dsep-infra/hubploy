import argparse
import hubploy
import sys
from hubploy import helm, auth, commitrange


def main():
    argparser = argparse.ArgumentParser()
    subparsers = argparser.add_subparsers(dest='command')
    build_parser = subparsers.add_parser('build', help='Build an image for a given deployment')

    build_parser.add_argument(
        'deployment',
        help='Name of deployment to build image of'
    )

    trigger_change_group = build_parser.add_mutually_exclusive_group()
    trigger_change_group.add_argument(
        '--commit-range',
        help='Trigger image rebuilds only if files in image directory have changed in this git commit range',
        default=commitrange.get_commit_range()
    )
    # FIXME: Needs a better name?
    trigger_change_group.add_argument(
        '--check-registry',
        action='store_true',
        help="Trigger image rebuild if image with expected name and tag is not in upstream registry."
    )
    build_parser.add_argument(
        '--push',
        action='store_true',
        help="Push image after building"
    )
    build_parser.add_argument(
        '--no-cache',
        action='store_true',
        help="Don't pull previous image to re-use cache from"
    )

    deploy_parser = subparsers.add_parser('deploy', help='Deploy a chart to the given environment')

    deploy_parser.add_argument(
        'deployment'
    )
    deploy_parser.add_argument(
        'chart'
    )
    deploy_parser.add_argument(
        'environment',
        choices=['develop', 'staging', 'prod']
    )
    deploy_parser.add_argument(
        '--namespace',
        default=None
    )
    deploy_parser.add_argument(
        '--set',
        action='append',
    )
    deploy_parser.add_argument(
        '--version',
    )
    deploy_parser.add_argument(
        '--timeout'
    )
    deploy_parser.add_argument(
        '--force',
        action='store_true'
    )
    deploy_parser.add_argument(
        '--atomic',
        action='store_true'
    )
    deploy_parser.add_argument(
        '--cleanup-on-fail',
        action='store_true'
    )

    args = argparser.parse_args()

    try:
        config = hubploy.config.get_config(args.deployment)
    except hubploy.config.DeploymentNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    if args.command == 'build':
        if not args.check_registry and not args.commit_range:
            # commit_range autodetection failed, and check registry isn't set
            # FIXME: Provide an actually useful error message
            print("Could not auto-detect commit-range, and --check-registry is not set", file=sys.stderr)
            print("Specify --commit-range manually, or pass --check-registry", file=sys.stderr)
            sys.exit(1)

        if args.push or args.check_registry:
            auth.registry_auth(args.deployment)

        for image in config.get('images', {}).get('images', {}):
            if image.needs_building(check_registry=args.check_registry, commit_range=args.commit_range):
                image.build(not args.no_cache)
                if args.push:
                    image.push()

    elif args.command == 'deploy':
        auth.cluster_auth(args.deployment)
        helm.deploy(args.deployment, args.chart, args.environment, args.namespace, args.set, args.version, args.timeout, args.force, args.atomic, args.cleanup_on_fail)

if __name__ == '__main__':
    main()