from setuptools import setup, find_packages

setup(
    name="pygame_physics",
    version="1.0.0",
    description="2D physics library for Pygame",
    author="Nikita Martynenko",
    packages=find_packages(),
    install_requires=["pygame"],
    python_requires=">=3.10",
)