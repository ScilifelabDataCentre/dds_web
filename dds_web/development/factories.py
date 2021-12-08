import factory
import os
import itertools
import random

import dds_web.database.models as models
from dds_web import db
from dds_web.crypt import key_gen


class UnitFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Unit
        sqlalchemy_session = db.session

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
                ProjectFactory.create_batch(
                    size=extracted, responsible_unit=self, unit_id=self.id, project_statuses=5
                )
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

    id = factory.Sequence(lambda n: n)

    responsible_unit = factory.SubFactory(UnitFactory)

    public_id = factory.Faker("uuid4")
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

    @factory.post_generation
    def project_statuses(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            if isinstance(extracted, int):
                ProjectStatusesFactory.create_batch(size=extracted, project=self)
            else:
                pass


class ProjectUserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.ProjectUsers
        sqlalchemy_session = db.session

    researchuser = factory.SubFactory(ResearchUserFactory)
    project = factory.SubFactory(ProjectFactory)


def random_status():
    choices = ["In Progress", "Deleted", "Available", "Expired", "Archived"]
    return random.choice(choices)


class ProjectStatusesFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.ProjectStatuses
        sqlalchemy_session = db.session

    project = factory.SubFactory(ProjectFactory)
    status = factory.LazyFunction(random_status)
    date_created = factory.Faker("date_time")


def create_all():
    factories = [UnitFactory, UnitUserFactory, ResearchUserFactory, ProjectFactory]
    for factory_class in factories:
        factory_class.reset_sequence(1)

    r_users = ResearchUserFactory.create_batch(50)
    UnitFactory.create_batch(3, projects=100, users=10)

    for unit in models.Unit.query.all():
        users = models.ResearchUser.query.all()
        projects = unit.projects
        if len(users) < len(projects):
            for project, user in zip(projects, itertools.cycle(users)):
                ProjectUserFactory(researchuser=user, project=project)
        else:
            for project, user in zip(itertools.cycle(projects), users):
                ProjectUserFactory(researchuser=user, project=project)

    db.session.commit()
