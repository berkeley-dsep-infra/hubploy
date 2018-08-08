import setuptools
from glob import glob

setuptools.setup(
    name='hubploy',
    version='0.1.0',
    url="https://github.com/yuvipanda/hubploy",
    author="Yuvi Panda",
    packages=setuptools.find_packages(),
    install_requires=[
        'requests'
    ]
)
