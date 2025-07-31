from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Define dependencies directly
requirements = [
    "rapidfuzz",
    "sentence-transformers>=2.2.2",
    "huggingface-hub<0.14.0",
    "transformers<4.30.0",
    "tqdm",
    "numpy",
    "pandas",
    "torch",
    "whoosh"
]

setup(
    name="adv-bible-search",
    version="0.1.1",
    author="Mahboob",
    author_email="siroosab@example.com",
    description="Advanced Bible Search Library with fuzzy and semantic search capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/siroosab/bible-search",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "bible-search=bible_search.search_cli:main",
        ],
    },
    include_package_data=True,
)
