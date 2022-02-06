from setuptools import setup, find_packages

setup(
    name='turbines',
    packages=find_packages(where='src'),  #
    version='0.0.1',
    license='MIT',
    description='Simple web framework for Python (obviously)',
    author='Nils Fast',                   # Type in your name
    author_email='',      # Type in your E-Mail
    url='https://github.com/nilsfast/turbines',
    keywords='web, framework, simple',
    install_requires=[],
    package_dir={'': 'src'},
    classifiers=[

        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
