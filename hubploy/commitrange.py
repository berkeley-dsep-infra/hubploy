import os
import json


def get_commit_range():
    """
    Auto detect commit range and return it if we can.
    Else return None
    """
    if 'GITHUB_ACTIONS' in os.environ:
        return get_commit_range_github()


def get_commit_range_github():
    with open(os.environ['GITHUB_EVENT_PATH']) as f:
        event = json.load(f)

    if 'pull_request' in event:
        base = event['pull_request']['base']['sha']
        return f'{base}...HEAD'
