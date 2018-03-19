========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis|
        | |coveralls| |codecov|
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|

.. |docs| image:: https://readthedocs.org/projects/django-delayed-union/badge/?style=flat
    :target: https://readthedocs.org/projects/django-delayed-union
    :alt: Documentation Status

.. |travis| image:: https://travis-ci.org/roverdotcom/django-delayed-union.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/roverdotcom/django-delayed-union

.. |coveralls| image:: https://coveralls.io/repos/roverdotcom/django-delayed-union/badge.svg?branch=master&service=github
    :alt: Coverage Status
    :target: https://coveralls.io/r/roverdotcom/django-delayed-union

.. |codecov| image:: https://codecov.io/github/roverdotcom/django-delayed-union/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/roverdotcom/django-delayed-union

.. |version| image:: https://img.shields.io/pypi/v/django-delayed-union.svg
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/django-delayed-union

.. |commits-since| image:: https://img.shields.io/github/commits-since/roverdotcom/django-delayed-union/v0.1.0.svg
    :alt: Commits since latest release
    :target: https://github.com/roverdotcom/django-delayed-union/compare/v0.1.0...master

.. |wheel| image:: https://img.shields.io/pypi/wheel/django-delayed-union.svg
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/django-delayed-union

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/django-delayed-union.svg
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/django-delayed-union

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/django-delayed-union.svg
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/django-delayed-union


.. end-badges

A library designed to workaround some drawbacks with Django's union, intersection, and difference operations.

* Free software: BSD 3-Clause License

Installation
============

::

    pip install django-delayed-union

Documentation
=============

https://django-delayed-union.readthedocs.io/

Development
===========

To run the all tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
