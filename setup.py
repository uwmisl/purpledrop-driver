from setuptools import setup, find_packages
import versioneer

setup(
    name="purpledrop",
    description="Driver software for controlling PurpleDrop digital microfluidic devices",
    long_description="""Provides bridge to control PurpleDrop USB device via HTTP API
or via  a browser based UI""",
    author="Jeff McBride",
    author_email="mcbridej@cs.washington.edu",
    url="https://github.com/uwmisl/purpledrop-driver",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'pdcam=purpledrop.script.pdcam:main',
            'pdcli=purpledrop.script.pd_cli:main',
            'pdserver=purpledrop.script.pd_server:main',
            'pdrecord=purpledrop.script.pd_record:main',
            'pdlog=purpledrop.script.pd_log:main',
        ],
    },
    install_requires=[
        'apriltag',
        'gevent~=20.5',
        'gevent-websocket~=0.10',
        'flask~=1.1',
        'flask-cors',
        'json-rpc~=1.13',
        'matplotlib',
        'opencv-python-headless',
        'protobuf',
        'pyserial',
        'requests',
    ],
    extras_require={
        'testing': [
            'pytest',
        ],
    },
    package_data={
        "purpledrop": ['frontend-dist.tar.gz', 'boards/*']
    }
)