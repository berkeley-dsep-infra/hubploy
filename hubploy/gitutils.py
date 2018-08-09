"""
Utilities for calling out to git
"""
import subprocess
import os


def last_git_modified(path, n=1):
    """Get last revision at which `path` got modified"""
    path = os.path.abspath(path)
    if os.path.isdir(path):
        cwd = path
    else:
        cwd = os.path.dirname(path)
    return subprocess.check_output([
        'git',
        'log',
        '-n', str(n),
        '--pretty=format:%h',
        path
    ], cwd=cwd).decode('utf-8').split('\n')[-1]