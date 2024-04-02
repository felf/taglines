#!/usr/bin/python3
# -*- coding:utf-8 -*-

if __name__ == "__main__":
    from distutils.core import setup
    import taglines
    setup(
        name="taglines",
        description="Taglines is an e-mail signature/fortune cookie tool.",
        long_description=taglines.__doc__,
        version=taglines.__version__,
        author="Frank Steinmetzger",
        author_email="dev@felsenfleischer.de",
        license="GPL",
        packages=["taglines"],
        scripts=["./Taglines"],
        classifiers=[
            "Development Status :: 4 - Beta",
            "Environment :: Console",
            "Intended Audience :: End Users/Desktop",
            "Natural Language :: English",
            "Operating System :: POSIX :: Linux",
            "Programming Language :: Python :: 3",
            "Topic :: Communications :: Email",
            "Topic :: Games/Entertainment :: Fortune Cookies"
        ]
    )
