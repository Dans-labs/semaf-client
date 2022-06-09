import codecs
import os
import re
from setuptools.command.test import test as TestCommand
from setuptools import find_packages
from setuptools import setup
import sys

CLASSIFIERS = [ 
     "Programming Language :: Python :: 3",
     "License :: OSI Approved :: Apache Software License",
     "Operating System :: OS Independent[options]"
     ]

INSTALL_REQUIREMENTS = [
"rdflib",
"numpy",
"pandas",
"bs4",
"bs2json",
"python_dateutil == 2.6.0",
"setuptools >= 21.0.0",
"pymongo",
"elasticsearch",
"pyDataverse == 0.2.1",
"aiofiles",
"jinja2",
"python-multipart"
        ]

setup(
name = "Semaf",
version = "0.0.4",
author = "Slava Tykhonov",
author_email = "vyacheslav.tykhonov@dans.knaw.nl",
description = "Client application using semantic mappings framework (SEMAF)",
long_description = "file: README.md",
long_description_content_type = "text/markdown",
url = "https://github.com/Dans-labs/semaf-client",
packages=find_packages("src"),
package_dir={"": "src"},
python_requires=">=3.6",
include_package_data = True
)
