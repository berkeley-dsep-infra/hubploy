from hubploy.registry import get_image_manifest, parse_www_authenticate

def test_www_authenticate():
    assert parse_www_authenticate("""
    Bearer realm="https://auth.docker.io/token",service="registry.docker.io",scope="repository:ubuntu:pull"
    """.strip()) == {
        'realm': 'https://auth.docker.io/token',
        'service': 'registry.docker.io',
        'scope': 'repository:ubuntu:pull'
    }

def test_existing_image():
    """
    Test that a known good image exists
    """
    manifest = get_image_manifest('https://registry-1.docker.io', 'library/ubuntu', '18.04')
    assert manifest is not None

def test_missing_image():
    """
    Test that a known-missing image does *not* exist
    """
    manifest = get_image_manifest('https://registry-1.docker.io', 'library/ubuntu', 'doesnotexist')
    assert manifest is None