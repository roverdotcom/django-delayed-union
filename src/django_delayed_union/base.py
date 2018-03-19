import abc
from builtins import object
from functools import partial

from django.db.models import QuerySet
from future.utils import with_metaclass


class DelayedQuerySetDescriptor(object):
    """
    A base class for the descriptors which are used for
    :class:`DelayedQuerySet`.

    Used in conjunction with :class:`DelayedQuerySetBase` in order to set
    their names upon class creation.
    """
    def __init__(self, name=None):
        self.name = name

    def set_name(self, name):
        """
        Sets the name of the descriptor to *name*.

        :param str name: the name of the descriptor
        """
        self.name = name


class DelayedQuerySetMethod(DelayedQuerySetDescriptor):
    """
    A descriptor which acts like a method on a class.  When accessed
    as an attribute on *obj*, it returns its ``__call__`` method with
    *obj* being passed in as the first argument.
    """
    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        return partial(self.__call__, obj)


class PostApplyMethod(DelayedQuerySetMethod):
    """
    When this descriptor is called, it runs :meth:`DelayedQuerySet._apply`
    first, and then calls the corresponding method on that result of
    that operation.

    For example, with a :class:`DelayedUnionQuerySet`, when we call
    ``count()`` on it, then this descriptor will first take the union
    of its component querysets and then call ``.count()`` on the result.
    """
    def __call__(self, obj, *args, **kwargs):
        return getattr(obj._apply(), self.name)(*args, **kwargs)


class PostApplyProperty(DelayedQuerySetDescriptor):
    """
    When this descriptor is called, it runs :meth:`DelayedQuerySet._apply`
    first, and then returns the corresponding property on the result of
    that operation.

    For example, with a :class:`DelayedUnionQuerySet`, when we access
    ``db`` on it, then this descriptor will first take the union
    of its component querysets and then return the ``db`` property on the
    result.
    """
    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        return getattr(obj._apply(), self.name)


class PassthroughMethod(DelayedQuerySetMethod):
    """
    When this descriptor is called, it calls the corresponding operation
    on all of the component querysets and then returns a clone of *obj*
    with those querysets.

    For example, when ``filter()`` is called on a :class:`DelayedUnionQuerySet`,
    it calls the corresponding filter method on all of the component
    querysets and then returns a :class:`DelayedUnionQuerySet` using
    those.
    """
    def __call__(self, obj, *args, **kwargs):
        return obj._clone([
            getattr(qs, self.name)(*args, **kwargs) for qs in obj._querysets
        ])


class FirstQuerySetPassthroughMethod(DelayedQuerySetMethod):
    """
    When this descriptor is called, returns a :class:`DelayedQuerySet`
    where the corresponding method has been applied to just the first
    component queryset.

    For example, when doing ``prefetch_related`` on a
    :class:`DelayedUnionQuerySet`, we only need to call ``prefetch_related``
    on the first queryset.  After the union is applied, then Django will
    use the prefetches from just that first queryset.
    """
    def __call__(self, obj, *args, **kwargs):
        querysets = (
            getattr(obj._querysets[0], self.name)(*args, **kwargs),
        ) + obj._querysets[1:]
        return obj._clone(querysets)


class FirstQuerySetMethod(DelayedQuerySetMethod):
    """
    When this descriptor is called, returns the result when calling the
    corresponding method on the first queryset.
    """
    def __call__(self, obj, *args, **kwargs):
        return getattr(obj._querysets[0], self.name)(*args, **kwargs)


class NotImplementedMethod(DelayedQuerySetMethod):
    """
    A descriptor which raises a :class:`NotImplementedError` when called.
    """
    def __call__(self, obj, *args, **kwargs):
        raise NotImplementedError()


class DelayedQuerySetBase(abc.ABCMeta):
    """
    This is the metaclass for :`DelayedQuerySet`.  It's purpose is to make
    sure that the names are set for all :class:`DelayedQuerySetDescriptor`
    instances in the class.
    """
    def __new__(cls, name, bases, attrs):
        for key, value in attrs.items():
            if isinstance(value, DelayedQuerySetDescriptor):
                value.set_name(key)
        return super(DelayedQuerySetBase, cls).__new__(cls, name, bases, attrs)


class DelayedQuerySet(with_metaclass(DelayedQuerySetBase, object)):
    """
    A class used to work around some of the issues with Django's built-in
    support for ``UNION`` within querysets.  The primary issue is that after
    a ``.union()`` call is made any subsequent filtering will silently fail.
    This works around that issue by maintaing all of the individual querysets
    and not applying an operation like ``.union()`` until it's needed.

    For example, suppose we have ``qs = DelayedUnionQuerySet(qs0, qs1)```,
    then running ``qs = qs.filter(id=42)`` will be equivalent to doing
    ``qs = DelayedUnionQuerySet(qs0.filter(id=42), qs1.filter(id=42))``. Then,
    when we actually need to evaluate the queryset say by doing
    ``obj = qs.first()``, it will return ``qs0.union(qs1).first()`` behind
    the scenes.

    Subclasses need to implement the :meth:`_apply_operation`, which performs
    the operation like ``.union()`` that is being delayed.
    """
    def __init__(self, *querysets, **kwargs):
        """
        :param tuple querysets: the component querysets
        :param dict kwargs: these are captured and made available for use
           in subclasses
        """
        if not all(isinstance(qs, QuerySet) for qs in querysets):
            # I think this should be able to work with DelayedQuerySets
            # as well, but the _apply method would need to call _apply
            # on any DelayedQuerySet in self._querysets
            raise ValueError('can only pass in QuerySets for now')
        self._querysets = tuple(qs.order_by() for qs in querysets)
        self._kwargs = kwargs
        self._standard_ordering = True
        self._order_by = ()

    def _apply(self):
        """
        Returns a :class:`django.db.models.QuerySet` where
        :meth:`_apply_operation` has been applied and the global ordering
        has been set.

        :rtype: :class:`django.db.models.QuerySet`
        """
        qs = self._apply_operation().order_by(*self._order_by)
        qs.query.standard_ordering = self._standard_ordering
        return qs

    @abc.abstractmethod
    def _apply_operation(self):
        """
        Returns a proper :class:`django.db.models.QuerySet` from the
        component queryset.  This is the operation that
        :class:`DelayedQuerySet` is delaying.

        For example, :class:`DelayedUnionQuerySet`
        runs :meth:`django.db.models.QuerySet.union` with all of the
        component querysets.

        :rtype: :class:`django.db.models.QuerySet`
        """

    @property
    def model(self):
        """
        Returns the model class for the :class:`DelayedQuerySet`.
        """
        return self._querysets[0].model

    def _clone(self, querysets=None):
        """
        Returns a copy of this :class:`DelayedQuerySet` with the ordering
        preserved.

        :parama querysets: an optional iterable of querysets to use in the
           in the clone
        """
        if querysets is None:
            querysets = [qs._clone() for qs in self._querysets]
        clone = type(self)(*querysets, **self._kwargs)
        clone._order_by = self._order_by
        clone._standard_ordering = self._standard_ordering
        return clone

    __repr__ = PostApplyMethod()
    __len__ = PostApplyMethod()
    __iter__ = PostApplyMethod()
    __bool__ = PostApplyMethod()
    __nonzero__ = PostApplyMethod()
    __getitem__ = PostApplyMethod()

    __deepcopy__ = NotImplementedMethod()
    __getstate__ = NotImplementedMethod()
    __setstate__ = NotImplementedMethod()
    __and__ = NotImplementedMethod()
    __or__ = NotImplementedMethod()

    iterator = PostApplyMethod()
    count = PostApplyMethod()
    earliest = PostApplyMethod()
    latest = PostApplyMethod()
    first = PostApplyMethod()
    last = PostApplyMethod()
    delete = PostApplyMethod()
    exists = PostApplyMethod()
    none = PassthroughMethod()
    raw = PostApplyMethod()

    db = PostApplyProperty()

    all = PassthroughMethod()
    filter = PassthroughMethod()
    exclude = PassthroughMethod()
    values = PassthroughMethod()
    values_list = PassthroughMethod()
    annotate = PassthroughMethod()
    dates = PassthroughMethod()
    datetimes = PassthroughMethod()
    select_related = PassthroughMethod()
    defer = PassthroughMethod()
    only = PassthroughMethod()
    extra = PassthroughMethod()
    using = PassthroughMethod()
    select_for_update = PassthroughMethod()
    complex_filter = PassthroughMethod()

    prefetch_related = FirstQuerySetPassthroughMethod()
    as_manager = FirstQuerySetPassthroughMethod()

    create = FirstQuerySetMethod()
    bulk_create = FirstQuerySetMethod()

    # These are left as not implemented at the moment.
    # We explicity put it here so that it is obvious to
    # the user of DelayedQuerysSet why things are not working.
    distinct = NotImplementedMethod()
    aggregate = NotImplementedMethod()
    union = NotImplementedMethod()
    intersection = NotImplementedMethod()
    difference = NotImplementedMethod()
    update = NotImplementedMethod()
    get_or_create = NotImplementedMethod()
    update_or_create = NotImplementedMethod()

    def get(self, *args, **kwargs):
        """
        Performs the query and returns a single object matching the given
        keyword arguments.

        .. note::

           We cannot use :class:`PostApplyMethod` for this since that does
           additional filtering which does not work with quersets that have
           been "unioned" for example.
        """
        clone = self.filter(*args, **kwargs)
        values = list(clone)
        num = len(values)
        if num == 1:
            return values[0]

        if not num:
            raise self.model.DoesNotExist(
                "%s matching query does not exist." %
                self.model._meta.object_name
            )
        raise self.model.MultipleObjectsReturned(
            "get() returned more than one %s -- it returned %s!" %
            (self.model._meta.object_name, num)
        )

    def order_by(self, *field_names):
        """
        Returns a new :class:`DelayedQuerySet`` instance with the ordering
        changed.

        .. note::

           We need to have a custom implementation for this because we
           want to change the ordering of the final queryset, not just
           the ordering within each component queryset.
        """
        qs = self._clone()
        qs._order_by = field_names
        return qs

    @property
    def ordered(self):
        """
        Returns True if the :class:`DelayedQuerySet` is ordered -- i.e.
        has an order_by() clause.

        :rtype: bool
        """
        return bool(self._order_by)

    def reverse(self):
        """
        Reverses the ordering of the :class:`DelayedQuerySet`.

        .. note::

           We need to have a custom implementation for this because we
           want to reverse the ordering of the final queryset, not just
           the ordering within each component queryset.
        """
        qs = self._clone()
        qs._standard_ordering = not qs._standard_ordering
        return qs

    def in_bulk(self, id_list=None):
        """
        Returns a dictionary mapping each of the given IDs to the object with
        that ID. If `id_list` isn't provided, the entire
        :class:`DelayedQuerySet` is evaluated.
        """
        if id_list is not None:
            if not id_list:
                return {}
            qs = self.filter(pk__in=id_list).order_by()
        else:
            qs = self._clone()
        return {obj._get_pk_val(): obj for obj in qs}
