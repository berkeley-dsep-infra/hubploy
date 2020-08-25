"""
Util to acquire a git commit range (get_commit_range) that represents the
changes that have triggered a certain CI system to run.

Current CI systems supported: GitHub Actions.
"""
import os
import json

from hubploy.utils import is_commit

def get_commit_range():
    """
    Auto detect commit range and return it if we can.
    Else return None
    """
    if 'GITHUB_ACTIONS' in os.environ:
        return get_commit_range_github()


def get_commit_range_github():
    """
    Auto detects commit range for pull requests and pushes from within a GitHub
    Action job using environment variables and .json file describing the event
    triggering the job.

    About env vars:     https://help.github.com/en/actions/configuring-and-managing-workflows/using-environment-variables
    About event file:   https://developer.github.com/webhooks/event-payloads/
    """
    with open(os.environ['GITHUB_EVENT_PATH']) as f:
        event = json.load(f)

    # pull_request ref: https://developer.github.com/webhooks/event-payloads/#pull_request
    if 'pull_request' in event:
        base = event['pull_request']['base']['sha']
        return f'{base}...HEAD'

    # push ref: https://developer.github.com/webhooks/event-payloads/#push
    if 'before' in event:
        if not is_commit(event['before']):
            print(f"A GitHub Actions environment was detected, but the constructed commit range ({event['before']}...HEAD) was invalid. This can happen if a git push --force has been run.")
            return None
        else:
            return f"{event['before']}...HEAD"
