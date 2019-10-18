from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.test import TestCase

from django_delayed_union import DelayedDifferenceQuerySet

from .factories import UserFactory
from .markers import skip_for_mysql
from .mixins import DelayedQuerySetMetaTestsMixin
from .mixins import DelayedQuerySetTestsMixin


class DelayedDifferenceQuerySetMetaTests(
        DelayedQuerySetMetaTestsMixin,
        TestCase):

    def get_class(self):
        return DelayedDifferenceQuerySet


class DelayedDifferenceQuerySetTestsMixin(DelayedQuerySetTestsMixin):
    pass


@skip_for_mysql
class DelayedDifferenceQuerySetTests(
        DelayedDifferenceQuerySetTestsMixin,
        TestCase):

    @classmethod
    def setUpTestData(cls):
        super(DelayedDifferenceQuerySetTests, cls).setUpTestData()
        cls.excluded_user = UserFactory.create()

    def get_queryset(self):
        return DelayedDifferenceQuerySet(
            User.objects.all(),
            User.objects.filter(id=self.excluded_user.id)
        )

    def get_expected_models(self):
        return [self.user]

    def test_select_related(self):
        base_qs = Permission.objects.all()
        qs = DelayedDifferenceQuerySet(base_qs, base_qs.none())

        self.assertTrue(qs.exists())
        for permission in qs.select_related('content_type'):
            with self.assertNumQueries(0):
                self.assertIsNotNone(permission.content_type.id)
