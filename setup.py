from setuptools import setup, find_packages

setup(
    name="purpledrop",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'pdcli=purpledrop.script.pd_cli:main',
            'pdserver=purpledrop.script.pd_server:main',
            'pdrecord=purpledrop.script.pd_record:main',
        ],
    },
    install_requires=[
        'gevent~=20.5',
        'gevent-websocket~=0.10',
        'flask~=1.1',
        'json-rpc~=1.13',
        'pyserial',
        'requests',
    ],
    extras_require={
        'testing': [
            'pytest',
        ],
    },
    package_data={
        "purpledrop": ['frontend-dist.tar.gz']
    }
)