from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.test import TestCase

from django_delayed_union import DelayedIntersectionQuerySet

from .factories import UserFactory
from .mixins import DelayedQuerySetMetaTestsMixin
from .mixins import DelayedQuerySetTestsMixin


class DelayedIntersectionQuerySetMetaTests(
        DelayedQuerySetMetaTestsMixin,
        TestCase):

    def get_class(self):
        return DelayedIntersectionQuerySet


class DelayedIntersectionQuerySetTestsMixin(DelayedQuerySetTestsMixin):
    pass


class DelayedIntersectionQuerySetTests(
        DelayedIntersectionQuerySetTestsMixin,
        TestCase):

    @classmethod
    def setUpTestData(cls):
        super(DelayedIntersectionQuerySetTests, cls).setUpTestData()
        cls.first_user = UserFactory.create()
        cls.second_user = UserFactory.create()

    def get_queryset(self):
        return DelayedIntersectionQuerySet(
            User.objects.exclude(id__in=[self.second_user.id]),
            User.objects.exclude(id__in=[self.first_user.id])
        )

    def test_select_related(self):
        base_qs = Permission.objects.all()
        qs = DelayedIntersectionQuerySet(base_qs, base_qs)

        self.assertTrue(qs.exists())
        for permission in qs.select_related('content_type'):
            with self.assertNumQueries(0):
                self.assertIsNotNone(permission.content_type.id)
