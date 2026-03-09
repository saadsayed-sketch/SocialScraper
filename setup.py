"""
Setup script for social media scraper
"""
from setuptools import setup, find_packages

setup(
    name="social-media-scraper",
    version="0.1.0",
    description="A browser automation system for scraping social media platforms",
    packages=find_packages(),
    install_requires=[
        "playwright>=1.40.0",
        "pytest>=7.4.3",
        "pytest-asyncio>=0.21.1",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)