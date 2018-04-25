from setuptools import setup

with open('requirements.txt') as fle:
    dependencies = fle.readlines()

setup(name='modelscraper',
      version='0.1',
      description='A scraper that allows for the reuse of different parts',
      author='Jim Lemmers',
      author_email='shout@jimlemmers.com',
      licenses='BSD',
      packages=['modelscraper'],
      install_requires=dependencies,
      zip_safe=False)

