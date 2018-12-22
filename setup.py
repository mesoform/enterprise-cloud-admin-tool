"""
@author: Gareth Brown
@contact: gareth@mesoform.com
@date: 2018
"""
import os
from setuptools import setup, find_packages

# See https://www.python.org/dev/peps/pep-0440 for version standards
MODULE_VERSION_MAJOR = 0
MODULE_VERSION_MINOR = 3


def __path(filename):
    return os.path.join(os.path.dirname(__file__), filename)


dir_path = os.path.dirname(os.path.realpath(__file__))
install_requirements = list(val.strip() for val in open(
    '{}/requirements.txt'.format(dir_path)))


build = 'dev1'
if os.path.exists(__path('build.info')):
    build = open(__path('build.info')).read().strip()

version = '{}.{}.{}'.format(MODULE_VERSION_MAJOR, MODULE_VERSION_MINOR, build)

setup(
    name='gcp_builder',
    version=version,
    packages=find_packages(dir_path, exclude=["test"]),
    package_dir={'enterprise_cloud_admin': dir_path},
    license='GPLv3',
    description='Package for managing enterprise cloud environments',
    long_description=open(__path('README.md')).read(),
    author='Gareth Brown',
    author_email='gareth@mesoform.com',
    scripts=['__init__.py'],
    url='https://bitbucket.org/mesoform/enterprise-cloud-admin.git',
    dependency_links=[],
    classifiers=[
        'BusinessUnit :: Cloud Services',
        'Projects :: Continuous Delivery'
    ],
    install_requires=install_requirements,
    data_files=[]
)
