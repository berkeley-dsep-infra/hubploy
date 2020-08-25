"""
Utils to extract information (last_modified_commit, path_touched) from the git
history.
"""
import subprocess


def first_alpha(s):
    """
    Returns the length of the shortest substring of the input that
    contains an alpha character.
    """
    for i, c in enumerate(s):
        if c.isalpha():
            return i + 1
    raise Exception("No alpha characters in string: {}".format(s))


def substring_with_alpha(s, min_len=7):
    """
    Returns the shortest substring of the input that
    contains an alpha character.

    Used to avoid helm/go bug that converts a string with all digit
    characters into an exponential.
    """
    return s[:max(min_len, first_alpha(s))]


def last_modified_commit(*paths, n=1, **kwargs):
    """Get the last commit to modify the given paths"""
    commit_hash = subprocess.check_output([
        'git',
        'log',
        '-n', str(n),
        '--pretty=format:%H',
        '--',
        *paths
    ], **kwargs).decode('utf-8').split('\n')[-1]
    return substring_with_alpha(commit_hash)


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


def is_commit(ref):
    try:
        subprocess.check_call(['git', 'cat-file', 'commit', ref])
        return True
    except subprocess.CalledProcessError:
        return False
