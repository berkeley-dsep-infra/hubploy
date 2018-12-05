"""
Utilities for calling out to git
"""
import subprocess
import os


def last_modified_commit(*paths, n=1, **kwargs):
    """Get the last commit to modify the given paths"""
    return subprocess.check_output([
        'git',
        'log',
        '-n', str(n),
        '--pretty=format:%h',
        '--',
        *paths
    ], **kwargs).decode('utf-8')


def last_modified_date(*paths, **kwargs):
    """Return the last modified date (as a string) for the given paths"""
    return subprocess.check_output([
        'git',
        'log',
        '-n', '1',
        '--pretty=format:%cd',
        '--date=iso',
        '--',
        *paths
    ], **kwargs).decode('utf-8')


def path_touched(*paths, commit_range):
    """Return whether the given paths have been changed in the commit range

    Used to determine if a build is necessary

    Args:
    *paths (str):
        paths to check for changes
    commit_range (str):
        range of commits to check if paths have changed
    """
    return subprocess.check_output([
        'git', 'diff', '--name-only', commit_range, '--', *paths
    ]).decode('utf-8').strip() != ''