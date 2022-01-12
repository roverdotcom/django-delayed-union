import abc
import inspect
from functools import partial

from django.db.models import QuerySet

from .utils import get_formatted_function_signature


class DelayedQuerySetDescriptor(abc.ABC):
    """
    A base class for the descriptors which are used for
    :class:`DelayedQuerySet`.

    Used in conjunction with :class:`DelayedQuerySetBase` in order to set
    their names upon class creation.
    """
    def __init__(self, name=None):
        self.set_name(name)

    def set_name(self, name):
        """
        Sets the name of the descriptor to *name*.

        :param str name: the name of the descriptor
        """
        self.name = name
        if name is not None:
            self.__doc__ = self.get_docstring()

    @abc.abstractmethod
    def get_base_docstring(self):
        """
        Returns a string which will be prepended to the docstring for
        the corresponding method on :class:`django.db.models.QuerySet`.
        """

    def get_docstring(self):
        """
        Returns a docstring for this descriptor based on the corresponding
        docstring for :class:`django.db.models.QuerySet`.
        """
        docstring = self.get_base_docstring().strip()

        queryset_attr = getattr(QuerySet, self.name, None)
        queryset_doc = getattr(queryset_attr, '__doc__', '')
        if queryset_doc:
            if docstring:
                docstring += '  Documentation for *{name}*:\n'
            docstring += queryset_doc

        if inspect.ismethod(queryset_attr):
            docstring = '{}{}\n{}'.format(
                self.name,
                get_formatted_function_signature(queryset_attr),
                docstring
            )
        return docstring.strip().format(name=self.name)


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

    def get_base_docstring(self):
        return """
        Returns the output of ``{name}(...)`` after having applied the delayed
        operation.
        """


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

    def __set__(self, obj, value):
        return setattr(obj._apply(), self.name, value)

    def get_base_docstring(self):
        return ""


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

    def get_base_docstring(self):
        return """
        Returns the a new delayed queryset with ``{name}(...)`` having been called
        on each of the component querysets.:
        """


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

    def get_base_docstring(self):
        return """
        Returns the a new delayed queryset with ``{name}(...)`` having been
        called on the first component queryset, while the rest remain unchanged.
        """


class FirstQuerySetMethod(DelayedQuerySetMethod):
    """
    When this descriptor is called, returns the result when calling the
    corresponding method on the first queryset.
    """
    def __call__(self, obj, *args, **kwargs):
        return getattr(obj._querysets[0], self.name)(*args, **kwargs)

    def get_base_docstring(self):
        return """
        Returns the result of calling ``{name}(...)`` on the first component
        queryset.
        """


class NotImplementedMethod(DelayedQuerySetMethod):
    """
    A descriptor which raises a :class:`NotImplementedError` when called.
    """
    def __call__(self, obj, *args, **kwargs):
        raise NotImplementedError()

    def get_base_docstring(self):
        return """
        Raises :class:`NotImplementedError`.
        """


class CountPostApplyMethod(PostApplyMethod):
    def __call__(self, obj, *args, **kwargs):
        # We make sure there are no select_related calls before calling
        # count to ensure we don't get an error on MySQL when doing
        # SELECT COUNT(*) from subquery where there are multiple columns
        # with the same name in subquery.
        if obj._result_cache is not None:
            return len(obj._result_cache)

        obj = obj.select_related(None)
        return super(CountPostApplyMethod, self).__call__(obj, *args, **kwargs)


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


class DelayedQuerySet(metaclass=DelayedQuerySetBase):
    """
    A class used to work around some of the issues with Django's built-in
    support for set operations with querysets (such as ``UNION``).
    The primary issue is that after ```.union()`` call is made any subsequent
    filtering will silently fail. This class works around that issue by
    maintaing all of the individual querysets and not applying an operation
    like ``.union()`` until it's needed.

    For example, suppose we have ``qs = DelayedUnionQuerySet(qs0, qs1)```,
    then running ``qs = qs.filter(id=42)`` will be equivalent to doing
    ``qs = DelayedUnionQuerySet(qs0.filter(id=42), qs1.filter(id=42))``. Then,
    when we actually need to evaluate the queryset say by doing
    ``obj = qs.first()``, it will return ``qs0.union(qs1).first()`` behind
    the scenes.

    Subclasses need to implement the :meth:`_apply_operation`, which performs
    the operation such as ``.union()`` that is being delayed.
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
            # on any DelayedQuerySet in self._querysets.  Additionally,
            # only certain database engines support nested set operations.
            raise ValueError('can only pass in QuerySets for now')
        self._querysets = tuple(qs.order_by() for qs in querysets)
        self._kwargs = kwargs
        self._standard_ordering = True
        self._order_by = ()
        self._applied = None  # a cache for the queryset after the operation has been applied

    def _apply(self):
        """
        Returns a :class:`django.db.models.QuerySet` where
        :meth:`_apply_operation` has been applied and the global ordering
        has been set.

        :rtype: :class:`django.db.models.QuerySet`
        """
        if self._applied is not None:
            return self._applied

        qs = self._apply_operation().order_by(*self._order_by)
        qs.query.standard_ordering = self._standard_ordering

        self._applied = qs
        return self._applied

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

    _result_cache = PostApplyProperty()
    _iterable_class = PostApplyProperty()

    _add_hints = PostApplyProperty()
    _hints = PostApplyProperty()

    query = PostApplyProperty()

    iterator = PostApplyMethod()
    count = CountPostApplyMethod()
    earliest = PostApplyMethod()
    latest = PostApplyMethod()
    first = PostApplyMethod()
    last = PostApplyMethod()
    delete = PostApplyMethod()
    exists = PostApplyMethod()
    contains = PostApplyMethod()
    none = PassthroughMethod()
    raw = PostApplyMethod()
    explain = PostApplyMethod()
    resolve_expression = PostApplyMethod()

    db = PostApplyProperty()

    all = PassthroughMethod()
    filter = PassthroughMethod()
    exclude = PassthroughMethod()
    values = PassthroughMethod()
    values_list = PassthroughMethod()
    annotate = PassthroughMethod()
    alias = PassthroughMethod()
    select_related = PassthroughMethod()
    defer = PassthroughMethod()
    only = PassthroughMethod()
    extra = PassthroughMethod()
    using = PassthroughMethod()
    complex_filter = PassthroughMethod()

    prefetch_related = FirstQuerySetPassthroughMethod()
    as_manager = FirstQuerySetPassthroughMethod()

    create = FirstQuerySetMethod()
    bulk_create = FirstQuerySetMethod()
    bulk_update = FirstQuerySetMethod()

    # These are left as not implemented at the moment.
    # We explicity put it here so that it is obvious to
    # the user of DelayedQuerysSet why things are not working.
    distinct = NotImplementedMethod()
    aggregate = NotImplementedMethod()
    union = NotImplementedMethod()
    intersection = NotImplementedMethod()
    difference = NotImplementedMethod()
    update = NotImplementedMethod()
    select_for_update = NotImplementedMethod()
    get_or_create = NotImplementedMethod()
    update_or_create = NotImplementedMethod()

    # These rely on sorting on an annotated field which is not available
    # once the union is applied
    dates = NotImplementedMethod()
    datetimes = NotImplementedMethod()

    def get(self, *args, **kwargs):
        """
        Performs the query and returns a single object matching the given
        keyword arguments.

        .. note::

           We cannot use :class:`PostApplyMethod` for this since that does
           additional filtering which does not work with querysets that have
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
