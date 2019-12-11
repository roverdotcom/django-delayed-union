from __future__ import unicode_literals

import factory
from django.contrib.auth.models import User
from django.utils import timezone


class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'username{n}')
    email = factory.Sequence(lambda n: f'email{n}@rover.com')

    first_name = factory.Sequence(lambda n: f'\xd3scarNumber{n}')
    last_name = factory.Sequence(lambda n: f'Ib\xe1\xf1ezNumber{n}')

    date_joined = factory.LazyAttribute(lambda user: timezone.now())

    @classmethod
    def _setup_next_sequence(cls):
        return 0
