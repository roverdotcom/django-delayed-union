from .base import DelayedQuerySet


class DelayedIntersectionQuerySet(DelayedQuerySet):
    def __init__(self, *querysets):
        return super(DelayedIntersectionQuerySet, self).__init__(*querysets)

    def _apply_operation(self):
        """
        Returs the union of all of the component querysets.
        """
        return self._querysets[0].intersection(*self._querysets[1:])

    def distinct(self):
        """
        Returns a new :class:`DelayedIntersectionQuerySet` instance that will
        select only distinct results.
        """
        clone = self._clone()
        return clone
