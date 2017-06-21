import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()
VERSION = open(os.path.join(here, 'VERSION.txt')).read().strip()

install_requires = [
    'python-dateutil',
]

setup(
    name='slovar',
    version=VERSION,
    description='slovar',
    long_description=README + '\n\n' +  CHANGES,
    classifiers=[
        "Programming Language :: Python",
    ],
    author='vahan',
    author_email='aivosha@gmail.com',
    url='',
    keywords='dict slovar',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
)
