from setuptools import setup, find_packages

def read_requirements(filename):
    with open(filename) as f:
        requirements = f.read().splitlines()
    return [req for req in requirements if req and not req.startswith('#')]

setup(
    name="voice-arxiv",
    version="0.1.0",
    packages=find_packages(),
    install_requires=read_requirements('requirements.txt'),
    python_requires=">=3.10",
)