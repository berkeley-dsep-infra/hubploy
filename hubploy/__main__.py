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

    build_parser.add_argument(
        '--image',
        # FIXME: Have a friendlier way to reference this
        help='Fully qualified docker image names to build',
        action='append'
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
        '--set-string',
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
        if not (args.check_registry or args.commit_range):
            args.commit_range = commitrange.get_commit_range()
            if not args.commit_range:
                # commit_range autodetection failed, and check registry isn't set
                # FIXME: Provide an actually useful error message
                print("Could not auto-detect commit-range, and --check-registry is not set", file=sys.stderr)
                print("Specify --commit-range manually, or pass --check-registry", file=sys.stderr)
                sys.exit(1)



        with auth.registry_auth(args.deployment, args.push, args.check_registry):

            all_images = config.get('images', {}).get('images', {})

            if args.image:
                build_images = [i for i in all_images if i.name in args.image]
            else:
                build_images = all_images

            print(f"Images found: {len(build_images)}")
            for image in build_images:
                if image.needs_building(check_registry=args.check_registry, commit_range=args.commit_range):
                    print(f"Building image {image.name}")
                    image.build(not args.no_cache)
                    if args.push:
                        image.push()
                else:
                    print(f"{image.name} does not require building")

    elif args.command == 'deploy':
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
        )

if __name__ == '__main__':
    main()