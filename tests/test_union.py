from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.test import TestCase

from django_delayed_union import DelayedUnionQuerySet

from .factories import UserFactory
from .mixins import DelayedQuerySetMetaTestsMixin
from .mixins import DelayedQuerySetTestsMixin


class DelayedUnionQuerySetMetaTests(DelayedQuerySetMetaTestsMixin, TestCase):
    def get_class(self):
        return DelayedUnionQuerySet

    def test_delayed_union_only_accepts_all_as_kwarg(self):
        with self.assertRaises(TypeError):
            DelayedUnionQuerySet(
                User.objects.all(),
                User.objects.all(),
                foo=42
            )


class DelayedUnionQuerySetTestsMixin(DelayedQuerySetTestsMixin):
    def test_select_related(self):
        base_qs = Permission.objects.all()
        qs = DelayedUnionQuerySet(base_qs, base_qs)

        self.assertTrue(qs.exists())
        for permission in qs.select_related('content_type'):
            with self.assertNumQueries(0):
                self.assertIsNotNone(permission.content_type.id)

    def test_update(self):
        self.qs.update(first_name='Rover')
        for user in self.qs:
            self.assertEqual(user.first_name, 'Rover')


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
        self.assertEqual(
            list(self.qs.values('id')),
            [{'id': self.user.id}, {'id': self.user.id}]
        )

    def test_values_list(self):
        self.assertEqual(
            list(self.qs.values_list('id', flat=True)),
            [self.user.id, self.user.id]
        )

    def test_len(self):
        self.assertEqual(len(self.qs), 2)

    def test_iterator(self):
        self.assertEqual(list(self.qs.iterator()), [self.user] * 2)
