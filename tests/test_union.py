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

    def get_expected_models(self):
        return [self.user]


class DelayedUnionQuerySetMixedTests(
        DelayedUnionQuerySetTestsMixin,
        TestCase):

    def get_queryset(self):
        return DelayedUnionQuerySet(
            User.objects.filter(id=self.bad_id),
            User.objects.all(),
        )

    def get_expected_models(self):
        return [self.user]


class DelayedUnionQuerySetReversedMixedTests(
        DelayedUnionQuerySetTestsMixin,
        TestCase):

    def get_queryset(self):
        return DelayedUnionQuerySet(
            User.objects.all(),
            User.objects.filter(id=self.bad_id),
        )

    def get_expected_models(self):
        return [self.user]


class DelayedUnionAllMutuallyExclusiveQuerySetTests(
        DelayedUnionQuerySetTestsMixin,
        TestCase):

    def get_queryset(self):
        return DelayedUnionQuerySet(
            User.objects.filter(id=self.user.id),
            User.objects.exclude(id=self.user.id),
            all=True
        )

    def get_expected_models(self):
        return [self.user]


class DelayedUnionAllQuerySetTests(DelayedUnionQuerySetTestsMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super(DelayedUnionQuerySetTestsMixin, cls).setUpTestData()
        cls.user_b = UserFactory.create()

    def get_queryset(self):
        return DelayedUnionQuerySet(
            User.objects.all(),
            User.objects.filter(id=self.user_b.id),
            all=True
        )

    def get_expected_models(self):
        return [self.user, self.user_b, self.user_b]

    def test_get_with_duplicates(self):
        with self.assertRaises(User.MultipleObjectsReturned):
            self.qs.get(id=self.user_b.id)
