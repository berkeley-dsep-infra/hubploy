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
    manifest = get_image_manifest('library/ubuntu:18.04')
    assert manifest is not None

    manifest = get_image_manifest('gcr.io/google-containers/busybox:1.27')
    assert manifest is not None

def test_missing_image():
    """
    Test that a known-missing image does *not* exist
    """
    # Test a tag that does not exist
    manifest = get_image_manifest('library/ubuntu:watwatwat')
    assert manifest is None

    manifest = get_image_manifest('gcr.io/google-containers/busybox:watwatwat')
    assert manifest is None

    # Test an *image* that does not exist.
    manifest = get_image_manifest('yuvipanda/8e338f70a44fe668673603da86ba:latest')
    assert manifest is None

    # Test an *image* that does not exist.
    manifest = get_image_manifest('gcr.io/google-containers/8e338f70a44fe668673603da86ba:latest')
    assert manifest is None