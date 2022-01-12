import factory
from django.contrib.auth.models import User
from django.utils import timezone


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: 'username{}'.format(n))
    email = factory.Sequence(lambda n: 'email{}@rover.com'.format(n))

    first_name = factory.Sequence(lambda n: '\xd3scarNumber{}'.format(n))
    last_name = factory.Sequence(lambda n: 'Ib\xe1\xf1ezNumber{}'.format(n))

    date_joined = factory.LazyAttribute(lambda user: timezone.now())

    @classmethod
    def _setup_next_sequence(cls):
        return 0
