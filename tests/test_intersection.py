from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.test import TestCase

from django_delayed_union import DelayedIntersectionQuerySet

from .factories import UserFactory
from .markers import skip_for_mysql
from .mixins import DelayedQuerySetMetaTestsMixin
from .mixins import DelayedQuerySetTestsMixin


class DelayedIntersectionQuerySetMetaTests(
        DelayedQuerySetMetaTestsMixin,
        TestCase):

    def get_class(self):
        return DelayedIntersectionQuerySet


@skip_for_mysql
class DelayedIntersectionQuerySetTestsMixin(DelayedQuerySetTestsMixin):
    def test_select_related(self):
        base_qs = Permission.objects.all()
        qs = DelayedIntersectionQuerySet(base_qs, base_qs)

        self.assertTrue(qs.exists())
        for permission in qs.select_related('content_type'):
            with self.assertNumQueries(0):
                self.assertIsNotNone(permission.content_type.id)


@skip_for_mysql
class DelayedIntersectionQuerySetTests(
        DelayedIntersectionQuerySetTestsMixin,
        TestCase):

    @classmethod
    def setUpTestData(cls):
        super(DelayedIntersectionQuerySetTests, cls).setUpTestData()
        cls.user_b, cls.user_c = UserFactory.create_batch(2)

    def get_queryset(self):
        return DelayedIntersectionQuerySet(
            User.objects.exclude(id=self.user_b.id),
            User.objects.exclude(id=self.user_c.id)
        )

    def get_expected_models(self):
        return [self.user]


@skip_for_mysql
class NestedDelayedIntersectionQuerySetTests(
        DelayedIntersectionQuerySetTestsMixin,
        TestCase):

    @classmethod
    def setUpTestData(cls):
        super(NestedDelayedIntersectionQuerySetTests, cls).setUpTestData()
        cls.user_b, cls.user_c, cls.user_d = UserFactory.create_batch(3)

    def get_queryset(self):
        return DelayedIntersectionQuerySet(
            User.objects.exclude(id=self.user_b.id),
            DelayedIntersectionQuerySet(
                User.objects.exclude(id=self.user_c.id),
                User.objects.exclude(id=self.user_d.id),
            )
        )

    def get_expected_models(self):
        return [self.user]
