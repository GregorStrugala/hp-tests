import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="vaplac",
    version="0.1",
    author="Gregor Strugala",
    author_email="gregor.strugala@polymtl.ca",
    description="Process and visualize data from DataTaker files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gstrugala/hp-tests",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
