import factory
import os

import dds_web.database.models as models
from dds_web import db
from dds_web.crypt import key_gen


class UnitFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Unit
        sqlalchemy_session = db.session
        sqlalchemy_get_or_create = ("id",)

    id = factory.Sequence(lambda n: n)
    name = factory.Sequence(lambda n: "Unit {}".format(n))
    public_id = factory.Faker("uuid4")
    external_display_name = "Display Name"
    contact_email = "support@example.com"
    internal_ref = factory.Sequence(lambda n: f"someunit {n}")
    safespring_endpoint = "endpoint"
    safespring_name = "dds.example.com"
    safespring_access = "access"
    safespring_secret = "secret"

    @factory.post_generation
    def users(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            if isinstance(extracted, int):
                UnitUserFactory.create_batch(size=extracted, unit=self)
            else:
                pass

    @factory.post_generation
    def projects(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            if isinstance(extracted, int):
                ProjectFactory.create_batch(size=extracted, unit=self)
            else:
                pass


class UnitUserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.UnitUser
        sqlalchemy_session = db.session

    username = factory.Sequence(lambda n: f"unit_user_{n}")
    password = "password"
    name = factory.Faker("name")

    unit = factory.SubFactory(UnitFactory)


class ResearchUserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.ResearchUser
        sqlalchemy_session = db.session

    username = factory.Sequence(lambda n: f"research_user_{n}")
    password = "password"
    name = factory.Faker("name")


class ProjectFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Project
        sqlalchemy_session = db.session

    unit = factory.SubFactory(UnitFactory)

    id = factory.Sequence(lambda n: n)

    public_id = factory.Faker("uuid4", unique=True)
    title = factory.Faker("sentence")
    description = factory.Faker("text")
    date_created = factory.Faker("date_time")
    pi = factory.Faker("name")
    bucket = factory.Faker("uuid4")

    privkey_salt = factory.LazyAttribute(
        lambda o: key_gen.ProjectKeys("Nonsense").key_dict()["privkey_salt"]
    )
    privkey_nonce = factory.LazyAttribute(
        lambda o: key_gen.ProjectKeys("Nonsense").key_dict()["privkey_nonce"]
    )
    public_key = factory.LazyAttribute(
        lambda o: key_gen.ProjectKeys("Nonsense").key_dict()["public_key"]
    )
    private_key = factory.LazyAttribute(
        lambda o: key_gen.ProjectKeys("Nonsense").key_dict()["private_key"]
    )


def create_all():
    unit_from_factory = UnitFactory.create(users=10, projects=10)
    db.session.add(unit)
    db.session.commit()
