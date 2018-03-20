=====
Usage
=====

To use Django Delayed Union in a project, import the wrapper corresponding
to the operation needed::

  from django_delayed_union import DelayedUnionQuerySet
  from django_delayed_union import DelayedIntersectionQuerySet
  from django_delayed_union import DelayedDifferenceQuerySet


Then, you use them where you would use Django's ``union``, ``intersection``, and
``difference`` methods::

  >>> qs0.union(qs1, qs2)
  >>> DelayedUnionQuerySet(qs0, qs1, qs2)

  >>> qs0.union(qs1, qs2, all=True)
  >>> DelayedUnionQuerySet(qs0, qs1, qs2, all=True)

  >>> qs0.intersection(qs1)
  >>> DelayedIntersectionQuerySet(qs0, qs1)

  >>> qs0.difference(qs1)
  >>> DelayedDifferenceQuerySet(qs0, qs1)

These wrappers implement the same public interface as Django's ``QuerySet``
so they should be able to be used by code which expects a ``QuerySet``.

.. note::

   ``DelayedQuerySet`` does not subclass ``QuerySet`` so any code
   which checks for whether or not an object is an instance of
   ``QuerySet`` will not work with these wrappers.

.. note::

   If certain methods are unimplemented or will not work, they will
   raise a ``NotImplementedError`` as opposed to silently not working.


Custom QuerySet methods
-----------------------

Currently, the wrappers do not handle any custom methods that may have
been added to the component querysets.  For example, if ``qs0`` and
``qs1`` were instances of a subclass of ``QuerySet`` that had an
``active()`` method, then the following would not work::

   >>> DelayedUnionQuerySet(q0, qs1).active()
   Traceback (most recent call last)
    ...
   AttributeError

Where this functionality is needed, it is straightforward to make a subclass
of ``DelayedUnionQuerySet`` using which has this behavior::

   from django_delayed_union.base import PassthroughMethod

   class MyDelayedUnionQuerySet(DelayedUnionQuerySet):
       active = PassthroughMethod()

   >>> MyDelayedUnionQuerySet(qs0, qs1).active()

Check out the other subclasses of
``django_delayed_union.base.DelayedQuerySetDescriptor`` if you need
the resulting method to behave differently than ``PassthroughMethod``.
