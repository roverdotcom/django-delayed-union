import abc
from builtins import object

from django.contrib.auth.models import User
from django.db.models import F
from django.db.models import Q
from django.db.models import QuerySet
from future.utils import with_metaclass

from django_delayed_union.base import DelayedQuerySetDescriptor

from .factories import UserFactory


class DelayedQuerySetMetaTestsMixin(with_metaclass(abc.ABCMeta, object)):
    @abc.abstractmethod
    def get_class(self):
        """
        Returns the subclass of :class:`DelayedQuerySet` to test.
        """

    def test_matches_public_api_of_queryset(self):
        cls = self.get_class()
        qs_attrs = set(dir(QuerySet))
        dqs_attrs = set(dir(cls))
        missing = filter(
            lambda attr: not attr.startswith('_'),
            qs_attrs - dqs_attrs
        )
        self.assertFalse(
            set(),
            (
                'The following attributes are missing'
                ' from {}: {}'
            ).format(cls, ', '.join(sorted(missing)))
        )

    def test_currently_does_not_support_nested_delayed_querysets(self):
        cls = self.get_class()
        with self.assertRaises(ValueError):
            cls(
                User.objects.all(),
                cls(User.objects.all(), User.objects.all())
            )

    def test_all_descriptors_have_docstrings(self):
        cls = self.get_class()
        for attr in dir(cls):
            descriptor = getattr(cls, attr)
            if not isinstance(descriptor, DelayedQuerySetDescriptor):
                continue
            self.assertIsNotNone(descriptor.__doc__)


class DelayedQuerySetTestsMixin(with_metaclass(abc.ABCMeta, object)):
    @classmethod
    def setUpTestData(cls):
        super(DelayedQuerySetTestsMixin, cls).setUpTestData()
        cls.user = UserFactory.create()
        cls.bad_id = cls.user.id - 1

    def setUp(self):
        super(DelayedQuerySetTestsMixin, self).setUp()
        self.regular_qs = User.objects.filter(id=self.user.id)
        self.qs = self.get_queryset()

    @abc.abstractmethod
    def test_select_related(self):
        """
        Subclasses should implement a test that select_related works.
        """

    def test_get(self):
        self.assertEqual(self.qs.get(id=self.user.id), self.user)

    def test_get_does_not_exist(self):
        with self.assertRaises(User.DoesNotExist):
            self.qs.get(id=self.bad_id)

    def test_get_multiple_objects_returned(self):
        UserFactory.create()
        with self.assertRaises(User.MultipleObjectsReturned):
            self.qs.get(id__gt=-1)

    def test_get_filtered_with_bad_id(self):
        with self.assertRaises(User.DoesNotExist):
            self.qs.filter(id=self.bad_id).get(id=self.user.id)

    def test_repr(self):
        self.assertEqual(repr(self.qs), repr(self.regular_qs))

    def test_contains_true(self):
        self.assertIn(self.user, self.qs)

    def test_contains_false(self):
        self.assertNotIn(self.user, self.qs.filter(id=self.bad_id))

    def test_bool_true(self):
        self.assertTrue(self.qs)

    def test_bool_false(self):
        self.assertFalse(self.qs.filter(id=self.bad_id))

    def test_getitem(self):
        self.assertEqual(self.qs[0], self.user)

    def test_count(self):
        self.assertEqual(self.qs.count(), 1)

    def test_iter(self):
        self.assertEqual(list(self.qs), [self.user])

    def test_filter(self):
        self.assertEqual(self.qs.filter(id=self.bad_id).count(), 0)

    def test_exclude(self):
        self.assertEqual(self.qs.exclude(id=self.user.id).count(), 0)

    def test_filtering_after_ordering(self):
        second = UserFactory.create()
        user = self.qs.order_by('-pk').exclude(id=self.bad_id).first()
        self.assertEqual(user, second)

    def test_values(self):
        self.assertEqual(
            list(self.qs.values('id')),
            [{'id': self.user.id}]
        )

    def test_values_list(self):
        self.assertEqual(
            list(self.qs.values_list('id', flat=True)),
            [self.user.id]
        )

    def test_prefetch_related(self):
        for user in self.qs.prefetch_related('groups'):
            with self.assertNumQueries(0):
                self.assertIsNotNone(user.groups.count())

    def test_prefetch_related_preserves_ordering(self):
        second = UserFactory.create()
        qs = self.qs.order_by('-pk').prefetch_related('groups')
        self.assertEqual(qs.first(), second)
        for user in qs:
            with self.assertNumQueries(0):
                self.assertIsNotNone(user.groups.count())

    def test_order_by(self):
        second = UserFactory.create()
        self.assertEqual(
            list(self.qs.order_by('id')),
            [self.user, second]
        )

    def test_order_by_reversed(self):
        second = UserFactory.create()
        self.assertEqual(
            list(self.qs.order_by('-id')),
            [second, self.user]
        )

    def test_ordered_false(self):
        self.assertFalse(self.qs.ordered)

    def test_ordered_true(self):
        self.assertTrue(self.qs.order_by('id').ordered)

    def test_reverse(self):
        second = UserFactory.create()
        self.assertEqual(
            list(self.qs.order_by('-id').reverse()),
            [self.user, second]
        )

    def test_len(self):
        self.assertEqual(len(self.qs), 1)

    def test_nonzero_true(self):
        self.assertTrue(self.qs)

    def test_nonzero_false(self):
        self.assertFalse(self.qs.filter(id=self.bad_id))

    def test_iterator(self):
        self.assertEqual(list(self.qs.iterator()), [self.user])

    def test_earliest(self):
        UserFactory.create()
        self.assertEqual(self.qs.earliest('pk'), self.user)

    def test_latest(self):
        second = UserFactory.create()
        self.assertEqual(self.qs.latest('pk'), second)

    def test_first(self):
        UserFactory.create()
        self.assertEqual(self.qs.first(), self.user)

    def test_first_with_ordering(self):
        second = UserFactory.create()
        self.assertEqual(self.qs.order_by('-pk').first(), second)

    def test_last(self):
        second = UserFactory.create()
        self.assertEqual(self.qs.last(), second)

    def test_last_with_ordering(self):
        UserFactory.create()
        self.assertEqual(self.qs.order_by('-pk').last(), self.user)

    def tests_exists_true(self):
        self.assertTrue(self.qs.exists())

    def tests_exists_false(self):
        self.assertFalse(self.qs.filter(id=self.bad_id).exists())

    def test_none(self):
        self.assertEqual(list(self.qs.none()), [])

    def test_db(self):
        self.assertEqual(self.qs.db, 'default')

    def test_annotate(self):
        user = self.qs.annotate(doubled=2 * F('id')).first()
        self.assertEqual(user.doubled, 2 * self.user.id)

    def test_only(self):
        user = self.qs.only('id').first()
        with self.assertNumQueries(0):
            self.assertEqual(user.id, self.user.id)
        with self.assertNumQueries(1):
            self.assertEqual(user.date_joined, self.user.date_joined)

    def test_defer(self):
        user = self.qs.defer('date_joined').first()
        with self.assertNumQueries(0):
            self.assertEqual(user.id, self.user.id)
        with self.assertNumQueries(1):
            self.assertEqual(user.date_joined, self.user.date_joined)

    def test_in_bulk(self):
        self.assertEqual(self.qs.in_bulk(), {self.user.id: self.user})

    def test_in_bulk_empty(self):
        self.assertEqual(self.qs.in_bulk([]), {})

    def test_in_bulk_with_ids(self):
        self.assertEqual(
            self.qs.in_bulk([self.user.id, self.bad_id]),
            {self.user.id: self.user}
        )

    def test_distinct(self):
        self.assertEqual(list(self.qs.distinct()), [self.user])

    def test_extra(self):
        user = self.qs.extra({'n': 'SELECT 42'}).first()
        self.assertEqual(user.n, 42)

    def test_using(self):
        qs = self.qs.using('some_db')
        self.assertEqual(qs.db, 'some_db')

    def test_create(self):
        user = self.qs.create()
        self.assertIsNotNone(user.id)

    def test_bulk_create(self):
        self.qs.bulk_create([User(id=4242)])
        self.assertTrue(User.objects.filter(id=4242).exists())

    def test_complex_filter(self):
        qs = self.qs.complex_filter(Q(id=-1))
        self.assertEqual(qs.count(), 0)

    def test_get_or_create(self):
        with self.assertRaises(NotImplementedError):
            self.qs.get_or_create(id=4242)
