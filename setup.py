from setuptools import setup

setup(name='ai2-brat',
      version='0.1',
      description='brat related utilities',
      url='http://github.com/allenai/brat',
      packages=['ai2_brat'],
      install_requires=["numpy",
                        "scipy",
                        "spacy",
                        "en-core-web-md"],
      zip_safe=False)
