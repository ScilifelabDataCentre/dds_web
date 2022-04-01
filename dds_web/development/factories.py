import factory
import itertools
import random
import flask

from dds_web.database import models
from dds_web import db

STATUSES_PER_PROJECT = 5
FILES_PER_PROJECT = 100
NR_UNITS = 10
USERS_PER_UNIT = 10
PROJECTS_PER_UNIT = 100
EMAILS_PER_USER = 3


class UnitFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Unit
        sqlalchemy_session = db.session

    id = factory.Sequence(lambda n: n)
    name = factory.Sequence(lambda n: f"Unit {n}")
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
                UnitUserFactory.create_batch(size=extracted, unit=self, emails=EMAILS_PER_USER)
            else:
                pass

    @factory.post_generation
    def projects(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            if isinstance(extracted, int):
                ProjectFactory.create_batch(
                    size=extracted,
                    responsible_unit=self,
                    unit_id=self.id,
                    project_statuses=STATUSES_PER_PROJECT,
                    files=FILES_PER_PROJECT,
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

    @factory.post_generation
    def emails(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            if isinstance(extracted, int):
                EmailFactory.create_batch(size=extracted, user=self)
            else:
                pass


class ResearchUserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.ResearchUser
        sqlalchemy_session = db.session

    username = factory.Sequence(lambda n: f"research_user_{n}")
    password = "password"
    name = factory.Faker("name")

    @factory.post_generation
    def emails(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            if isinstance(extracted, int):
                EmailFactory.create_batch(size=extracted, user=self)
            else:
                pass


class EmailFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Email
        sqlalchemy_session = db.session

    id = factory.Sequence(lambda n: n)
    email = factory.Faker("email")
    primary = factory.Faker("boolean")


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

    @factory.post_generation
    def project_statuses(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            if isinstance(extracted, int):
                ProjectStatusesFactory.create_batch(size=extracted, project=self)
            else:
                pass

    @factory.post_generation
    def files(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            if isinstance(extracted, int):
                FilesFactory.create_batch(size=extracted, project=self)
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


def random_filesize():
    """returns a"""
    nr_bits = random.randint(1, 40)
    return random.getrandbits(nr_bits)


class FilesFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.File
        sqlalchemy_session = db.session

    project = factory.SubFactory(ProjectFactory)
    name = factory.Faker("file_name")
    name_in_bucket = factory.Faker("text")
    subpath = factory.Faker("file_name")
    size_original = factory.LazyFunction(random_filesize)
    size_stored = factory.LazyFunction(random_filesize)
    compressed = factory.Faker("boolean")
    public_key = factory.Faker("pystr", min_chars=64, max_chars=64)
    salt = factory.Faker("pystr", min_chars=32, max_chars=32)
    checksum = factory.Faker("pystr", min_chars=64, max_chars=64)
    time_latest_download = factory.Faker("date_time")

    # versions


def create_all():
    factories = [
        UnitFactory,
        UnitUserFactory,
        ResearchUserFactory,
        EmailFactory,
        ProjectFactory,
        ProjectUserFactory,
        ProjectStatusesFactory,
        FilesFactory,
    ]
    for factory_class in factories:
        factory_class.reset_sequence(1)

    r_users = ResearchUserFactory.create_batch(50, emails=EMAILS_PER_USER)
    flask.current_app.logger.info("Created research users")
    for i in range(NR_UNITS):
        UnitFactory.create(projects=PROJECTS_PER_UNIT, users=USERS_PER_UNIT)
        flask.current_app.logger.info(f"Created unit {i}")

    for unit in models.Unit.query.all():
        users = models.ResearchUser.query.all()
        projects = unit.projects
        if len(users) < len(projects):
            for project, user in zip(projects, itertools.cycle(users)):
                ProjectUserFactory(researchuser=user, project=project)
        else:
            for project, user in zip(itertools.cycle(projects), users):
                ProjectUserFactory(researchuser=user, project=project)
    flask.current_app.logger.info("Created project user associations")

    db.session.commit()
