import argparse
from hubploy import imagebuilder, helm, auth
import docker


def main():
    argparser = argparse.ArgumentParser()
    subparsers = argparser.add_subparsers(dest='command')
    build_parser = subparsers.add_parser('build', help='Build an image from given path')

    build_parser.add_argument(
        'deployment',
        help='Path to directory with dockerfile'
    )
    build_parser.add_argument(
        '--commit-range',
        help='Trigger image rebuilds only if path has changed in this commit range'
    )
    build_parser.add_argument(
        '--push',
        action='store_true',
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

    args = argparser.parse_args()

    if args.command == 'build':
        client = docker.from_env()
        if args.push:
            auth.registry_auth(args.deployment)
        imagebuilder.build_deployment(client, args.deployment, args.commit_range, args.push)
    elif args.command == 'deploy':
        helm.deploy(args.deployment, args.chart, args.environment, args.namespace, args.set, args.version)