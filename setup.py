from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="das_nidf",
    version="1.0.2",
    author="Miguel A Saavedra L",
    author_email="miguel.lozano@lps.ufrj.br",
    description="Distributed Acoustic Sensing  Processing and Data Visualization Library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MSL01/DAS-PROCESSING-AND-VISUALIZATION.git",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Visualization",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "scipy>=1.7.0",
        "h5py>=3.0.0",
        "holoviews>=1.15.0",
        "datashader>=0.14.0",
        "bokeh>=3.9.0",
        "scikit-image>=0.19.0",
        "matplotlib>=3.4.0",
        "colorcet>=3.0.0",
        "Flask>=2.0.0",
        "itsdangerous>=2.0.0",
        "flask-cors>=4.0.0",
    ],
    extras_require={
        "dev": ["pytest>=6.0", "jupyter"],
        "full": ["matplotlib>=3.4.0", "tqdm>=4.62.0"],
    },
)