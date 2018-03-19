import abc

import pytest
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.db import DatabaseError
from django.db.models import F
from django.db.models import Q
from django.db.models import QuerySet
from django.test import TestCase

from django_delayed_union import DelayedUnionQuerySet
from django_delayed_union.base import DelayedQuerySetBase
from django_delayed_union.base import DelayedQuerySetDescriptor

from .factories import UserFactory


class DelayedQuerySetBaseTests(TestCase):
    def setUp(self):
        super(DelayedQuerySetBaseTests, self).setUp()
        self.cls = DelayedUnionQuerySet

    def test_has_metaclass(self):
        self.assertTrue(
            issubclass(type(self.cls), DelayedQuerySetBase)
        )

    def test_descriptors_have_names_set(self):
        for name in dir(self.cls):
            descriptor = getattr(self.cls, name)
            if not isinstance(descriptor, DelayedQuerySetDescriptor):
                continue
            self.assertEqual(descriptor.name, name)


class DelayedQuerySetMetaTests(TestCase):
    def test_matches_public_api_of_queryset(self):
        qs_attrs = set(dir(QuerySet))
        dqs_attrs = set(dir(DelayedUnionQuerySet))
        missing = filter(
            lambda attr: not attr.startswith('_'),
            qs_attrs - dqs_attrs
        )
        self.assertFalse(
            set(),
            (
                'The following attributes are missing'
                ' from DelayedQuerySet: {}'
            ).format(', '.join(sorted(missing)))
        )

    def test_delayed_union_only_accepts_all_as_kwarg(self):
        with self.assertRaises(TypeError):
            DelayedUnionQuerySet(
                User.objects.all(),
                User.objects.all(),
                foo=42
            )

    def test_currently_does_not_support_nested_delayed_querysets(self):
        with self.assertRaises(ValueError):
            DelayedUnionQuerySet(
                User.objects.all(),
                DelayedUnionQuerySet(User.objects.all(), User.objects.all())
            )


class DelayedUnionQuerySetTestsMixin(object):
    __metaclass__ = abc.ABCMeta

    @classmethod
    def setUpTestData(cls):
        super(DelayedUnionQuerySetTestsMixin, cls).setUpTestData()
        cls.user = UserFactory.create()
        cls.bad_id = cls.user.id - 1

    def setUp(self):
        super(DelayedUnionQuerySetTestsMixin, self).setUp()
        self.regular_qs = User.objects.all()
        self.qs = self.get_queryset()

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

    def test_select_related(self):
        base_qs = Permission.objects.all()
        qs = DelayedUnionQuerySet(base_qs, base_qs)

        self.assertTrue(base_qs.exists())
        for permission in qs.select_related('content_type'):
            with self.assertNumQueries(0):
                self.assertIsNotNone(permission.content_type.id)

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

    @pytest.mark.xfail(strict=True, raises=DatabaseError)
    def test_dates(self):
        self.assertEqual(
            self.qs.dates('date_joined', 'day').first(),
            self.user.date_joined.date()
        )

    @pytest.mark.xfail(strict=True, raises=DatabaseError)
    def test_datetimes(self):
        self.assertEqual(
            self.qs.datetimes('date_joined', 'second').first(),
            self.user.date_joined
        )

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

    def test_select_for_update(self):
        self.assertIsNotNone(self.qs.select_for_update().first())

    def test_update(self):
        self.qs.update(first_name='Rover')
        for user in self.qs:
            self.assertEqual(user.first_name, 'Rover')

    def test_complex_filter(self):
        qs = self.qs.complex_filter(Q(id=-1))
        self.assertEqual(qs.count(), 0)

    def test_get_or_create(self):
        with self.assertRaises(NotImplementedError):
            self.qs.get_or_create(id=4242)


class DelayedUnionQuerySetTests(DelayedUnionQuerySetTestsMixin, TestCase):
    def get_queryset(self):
        return DelayedUnionQuerySet(
            User.objects.all(),
            User.objects.all(),
        )


class DelayedUnionQuerySetMixedTests(
        DelayedUnionQuerySetTestsMixin,
        TestCase):

    def get_queryset(self):
        return DelayedUnionQuerySet(
            User.objects.filter(id=self.bad_id),
            User.objects.all(),
        )


class DelayedUnionQuerySetReversedMixedTests(
        DelayedUnionQuerySetTestsMixin,
        TestCase):

    def get_queryset(self):
        return DelayedUnionQuerySet(
            User.objects.all(),
            User.objects.filter(id=self.bad_id),
        )


class DelayedUnionAllMutuallyExclusiveQuerySetTests(
        DelayedUnionQuerySetTestsMixin,
        TestCase):

    def get_queryset(self):
        return DelayedUnionQuerySet(
            User.objects.filter(id=self.user.id),
            User.objects.exclude(id=self.user.id),
            all=True
        )


class DelayedUnionAllQuerySetTests(DelayedUnionQuerySetTestsMixin, TestCase):

    def get_queryset(self):
        return DelayedUnionQuerySet(
            User.objects.all(),
            User.objects.all(),
            all=True
        )

    def test_get(self):
        with self.assertRaises(User.MultipleObjectsReturned):
            self.qs.get(id=self.user.id)

    def test_repr(self):
        self.assertEqual(
            repr(self.qs),
            '<QuerySet {}>'.format([self.user, self.user])
        )

    def test_count(self):
        self.assertEqual(self.qs.count(), 2)

    def test_iter(self):
        self.assertEqual(list(self.qs), [self.user, self.user])

    def test_order_by(self):
        second_user = UserFactory.create()
        self.assertEqual(
            list(self.qs.order_by('pk')),
            [self.user] * 2 + [second_user] * 2
        )

    def test_order_by_reversed(self):
        second_user = UserFactory.create()
        self.assertEqual(
            list(self.qs.order_by('-pk')),
            [second_user] * 2 + [self.user] * 2
        )

    def test_reverse(self):
        second_user = UserFactory.create()
        self.assertEqual(
            list(self.qs.order_by('pk').reverse()),
            [second_user] * 2 + [self.user] * 2
        )

    def test_values(self):
        self.assertEqual(list(self.qs.values('id')), [{'id': 1}, {'id': 1}])

    def test_values_list(self):
        self.assertEqual(list(self.qs.values_list('id', flat=True)), [1, 1])

    def test_len(self):
        self.assertEqual(len(self.qs), 2)

    def test_iterator(self):
        self.assertEqual(list(self.qs.iterator()), [self.user] * 2)
