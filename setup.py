import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="tinytuya",
    version="1.7.3",
    author="Jason Cox",
    author_email="jason@jasonacox.com",
    description="Python module to interface with Tuya WiFi smart devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/jasonacox/tinytuya',
    packages=setuptools.find_packages(exclude=("sandbox",)),
    install_requires=[
        'pycryptodome',  # Encryption - AES can also be provided via PyCrypto or pyaes
        'requests',      # Used for Setup Wizard - Tuya IoT Platform calls
        'colorama',      # Makes ANSI escape character sequences work under MS Windows.
    ],
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
