import os
from setuptools import setup

from route53_transfer import __version__


def read(filename):
    fullpath = os.path.join(os.path.dirname(__file__), filename)
    return open(fullpath, 'r', encoding='utf-8').read()


setup(name='route53-transfer-ng',
      version=__version__,
      description='Backup and restore Route53 zones, or transfer between AWS accounts.',
      long_description=read('README.md'),
      url='http://github.com/cosimo/route53-transfer-ng',
      author='Cosimo Streppone',
      author_email='cosimo@cpan.org',
      license='Apache License 2.0',
      packages=['route53_transfer'],
      scripts=['bin/route53-transfer-ng'],
      tests_require=open('test-requirements.txt').readlines(),
      install_requires=open('requirements.txt').readlines(),
      python_requires='>=3.6',
      classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Topic :: Utilities',
        'Operating System :: OS Independent',
      ])
