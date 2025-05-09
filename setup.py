import setuptools

setuptools.setup(
    name="hubploy",
    version="0.4.2",
    url="https://github.com/berkeley-dsep-infra/hubploy",
    author="Yuvi Panda and Shane Knapp",
    packages=setuptools.find_packages(),
    install_requires=["kubernetes", "boto3"],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "hubploy = hubploy.__main__:main",
        ],
    },
)
