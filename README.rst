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
        | |codecov|
    * - package
      - | |version| |wheel| |django-versions| |supported-versions|
        | |commits-since|

.. |docs| image:: https://readthedocs.org/projects/django-delayed-union/badge/?style=flat
    :target: https://readthedocs.org/projects/django-delayed-union
    :alt: Documentation Status

.. |travis| image:: https://travis-ci.org/roverdotcom/django-delayed-union.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/roverdotcom/django-delayed-union

.. |codecov| image:: https://codecov.io/github/roverdotcom/django-delayed-union/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/roverdotcom/django-delayed-union

.. |version| image:: https://img.shields.io/pypi/v/django-delayed-union.svg
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/django-delayed-union

.. |commits-since| image:: https://img.shields.io/github/commits-since/roverdotcom/django-delayed-union/v0.1.7.svg
    :alt: Commits since latest release
    :target: https://github.com/roverdotcom/django-delayed-union/compare/v0.1.7...master

.. |wheel| image:: https://img.shields.io/pypi/wheel/django-delayed-union.svg
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/django-delayed-union

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/django-delayed-union.svg
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/django-delayed-union

.. |django-versions| image:: https://img.shields.io/pypi/djversions/django-delayed-union.svg
   :alt: Django versions
   :target: https://pypi.python.org/pypi/django-delayed-union


.. end-badges

``django-delayed-union`` is library designed to workaround some
drawbacks with Django's union, intersection, and difference
operations.  In particular, once one of these operations is performed,
certain methods on the queryset will silently not work::

  >>> qs = User.objects.filter(id=1)
  >>> unioned_qs = qs.union(qs)
  >>> should_be_empty_qs = unioned_qs.exclude(id=1)
  >>> user, = list(should_be_empty_qs); user.id
  1

In order to work around this, ``django-delayed-union`` provides
wrappers around a collection of querysets.  These wrappers implement a
similar interface to ``QuerySet``, and delay performing the union,
intersection, or difference operations until they are needed::

  >>> from django_delayed_union import DelayedUnionQuerySet
  >>> qs = User.objects.filter(id=1)
  >>> unioned_qs = DelayedUnionQuerySet(qs, qs)
  >>> empty_qs = unioned_qs.exclude(id=1)
  >>> list(empty_qs)
  []

Operations which would typically return a new ``QuerySet`` instead
return a new ``DelayedQuerySet`` with the operation applied to its
collection of querysets.

One example of where this code has been useful with is when the the
MySQL query planner has chosen an inefficient query plan for the
queryset of a `Django REST Framework <https://github.com/foo/>`_ view
which used an ``OR`` condition.  By using ``DelayedUnionQuerySet``,
subclasses could perform additional filters on the queryset while
still maintaining the efficient query plan.

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
