"""USED ONLY DURING DEVELOPMENT! Adds test data to the database."""

import os
import uuid

from flask import current_app

from dds_web import db, timestamp

from dds_web.database.models import User, Project, Facility, File


# def create_files_for_project(project):
#     """ Get a project model and creates dummy test file structure for it """

#     files_list = [
#         {
#             'name': '{}_description.txt',
#             'dpath': '',
#             'size': '146 kb'
#         },
#         {
#             'name': 'Sample_1/{}_data.txt',
#             'dpath': 'Sample_1',
#             'size': '10.3 mb'
#         },
#         {
#             'name': 'Sample_1/{}_source.txt',
#             'dpath': 'Sample_1',
#             'size': '257 kb'
#         },
#         {
#             'name': 'Sample_1/meta/{}_info.txt',
#             'dpath': 'Sample_1/meta',
#             'size': '96 kb'
#         },
#         {
#             'name': 'Sample_2/{}_data.txt',
#             'dpath': 'Sample_2',
#             'size': '8.7 mb'
#         },
#         {
#             'name': 'Sample_2/{}_source.txt',
#             'dpath': 'Sample_2',
#             'size': '350 kb'
#         },
#         {
#             'name': 'Sample_2/meta/{}_info.txt',
#             'dpath': 'Sample_2/meta',
#             'size': '67 kb'
#         },
#         {
#             'name': '{}_sample_list.txt',
#             'dpath': '',
#             'size': '18 kb'
#         },
#         {
#             'name': 'Plates/Sample_1/{}_layout.txt',
#             'dpath': 'Plates/Sample_1',
#             'size': '79 kb'
#         },
#         {
#             'name': 'Plates/Sample_2/{}_layout.txt',
#             'dpath': 'Plates/Sample_2',
#             'size': '95 kb'
#         }
#     ]

# for fnum, finfo in enumerate(files_list):
#     mfile = File(name=finfo['name'].format(project.id), directory_path=finfo['dpath'],
#                  size=1, size_enc=1, extension='ext', compressed=True,
#                  public_key='public_key', salt='salt',
#                  time_uploaded='2020-05-25', project_id=project
#                  )
#     project.project_files.append(mfile)


def fill_db():
    """Fills the database with initial entries used for development."""

    facilities = [
        Facility(
            public_id="public_facility_id",
            name="Facility 1",
            internal_ref="fac",
            safespring=current_app.config.get("DDS_SAFE_SPRING_PROJECT"),
        )
    ]

    projects = [
        Project(
            public_id="public_project_id",
            title="project_title",
            category="Category",
            date_created=timestamp(),
            date_updated=timestamp(),
            status="Ongoing",
            description="This is a test project",
            pi="PI",
            size=7357,
            bucket=f"publicproj-{str(timestamp(ts_format='%Y%m%d%H%M%S'))}-{str(uuid.uuid4())}",
            public_key="08D0D813DD7DD2541DF58A7E5AB651D20299F741732B0DC8B297A2D4CB43626C",
            private_key="5F39E1650CC7592EF2A06FDD37FB576EFE19C1C0C4FBDF0C799EBE19FD4B731805C25213D9398B09A7F3A0CCADA71B7E",
            privkey_salt="C2BB3FB2BBBA0DD01A6A2F5937C9D84C",
            privkey_nonce="D652B8C4554B675FB780A6EE",
            facility_id=facilities[0],
        )
    ]

    users = [
        User(
            username="username",
            password="$argon2id$v=19$m=102400,t=2,p=8$0jcemW3Ln+HTPUt/E3xtKQ$aZGqrrBBU5gq5TbWYwUWD62UiQUmTksbKOkmbMJzdhs",
            role="researcher",
            permissions="-gl--",
            facility_id=None,
        ),
        User(
            username="admin",
            password="$argon2id$v=19$m=102400,t=2,p=8$0jcemW3Ln+HTPUt/E3xtKQ$aZGqrrBBU5gq5TbWYwUWD62UiQUmTksbKOkmbMJzdhs",
            role="admin",
            permissions="a-l--",
            facility_id=None,
        ),
        User(
            username="facility_admin",
            password="$argon2id$v=19$m=102400,t=2,p=8$0jcemW3Ln+HTPUt/E3xtKQ$aZGqrrBBU5gq5TbWYwUWD62UiQUmTksbKOkmbMJzdhs",
            role="facility",
            permissions="a-l--",
            facility_id=facilities[0],
        ),
        User(
            username="facility",
            password="$argon2id$v=19$m=102400,t=2,p=8$0jcemW3Ln+HTPUt/E3xtKQ$aZGqrrBBU5gq5TbWYwUWD62UiQUmTksbKOkmbMJzdhs",
            role="facility",
            permissions="--lpr",
            facility_id=facilities[0],
        ),
    ]

    # User(
    #     public_id="public_admin_id",
    #     username="admin",
    #     password="$argon2id$v=19$m=102400,t=2,p=8$0jcemW3Ln+HTPUt/E3xtKQ$aZGqrrBBU5gq5TbWYwUWD62UiQUmTksbKOkmbMJzdhs",
    #     role="admin",
    #     permissions="a-l--",
    # )
    #     User(first_name="FirstName", last_name="LastName",
    #         username="username1",
    #         password=("9f247257e7d0ef00ad5eeeda7740233167d36b265a918536b8"
    #                   "c27a8efd774bc5"),
    #         settings="41ec11c65b21a72b0ef38c6cd343e62b$32$14$8$1",
    #         email="user1@email.com", phone="070-000 00 01",
    #         admin=False),
    #     User(first_name="Han", last_name="Solo",
    #         username="hanflysolo",
    #         password=("9f247257e7d0ef00ad5eeeda7740233167d36b265a918536b8"
    #                   "c27a8efd774bc5"),
    #         settings="41ec11c65b21a72b0ef38c6cd343e62b$32$14$8$1",
    #         email="user2@email.com", phone="070-000 00 01",
    #         admin=False),
    #     User(first_name="Tony", last_name="Stark",
    #         username="tonyistony",
    #         password=("9f247257e7d0ef00ad5eeeda7740233167d36b265a918536b8"
    #                   "c27a8efd774bc5"),
    #         settings="41ec11c65b21a72b0ef38c6cd343e62b$32$14$8$1",
    #         email="user3@email.com", phone="070-000 00 01",
    #         admin=False),
    #     User(first_name="Katniss", last_name="Everdeen",
    #         username="katever",
    #         password=("9f247257e7d0ef00ad5eeeda7740233167d36b265a918536b8"
    #                   "c27a8efd774bc5"),
    #         settings="41ec11c65b21a72b0ef38c6cd343e62b$32$14$8$1",
    #         email="user4@email.com", phone="070-000 00 01",
    #         admin=False)
    # ]

    # Facility(name="Facility1", internal_ref="fac1",
    #          username="facility1",
    #          password=("b93be04bfdcdace50c5f5d8e88a3e08e2d6fdd1258"
    #                    "095735f5a395e9013d70ec"),
    #          settings="41ec11c65b21a72b0ef38c6cd343e62b$32$14$8$1",
    #          email="supprt@fac.se", phone="08 000 00 00"),
    # Facility(name="Genome facility", internal_ref="fac2",
    #          username="genome_fac",
    #          password=("b93be04bfdcdace50c5f5d8e88a3e08e2d6fdd1258"
    #                    "095735f5a395e9013d70ec"),
    #          settings="41ec11c65b21a72b0ef38c6cd343e62b$32$14$8$1",
    #          email="supprt@genome.se", phone="08 000 00 00"),
    # Facility(name="Imaging facility", internal_ref="fac3",
    #          username="image_fac",
    #          password=("b93be04bfdcdace50c5f5d8e88a3e08e2d6fdd1258"
    #                    "095735f5a395e9013d70ec"),
    #          settings="41ec11c65b21a72b0ef38c6cd343e62b$32$14$8$1",
    #          email="supprt@imaging.se", phone="08 000 00 00"),
    # Facility(name="Proteomics facility", internal_ref="fac4",
    #          username="proteome_fac",
    #          password=("b93be04bfdcdace50c5f5d8e88a3e08e2d6fdd1258"
    #                    "095735f5a395e9013d70ec"),
    #          settings="41ec11c65b21a72b0ef38c6cd343e62b$32$14$8$1",
    #          email="supprt@proteome.se", phone="08 000 00 00")
    # ]

    files = [
        File(
            public_id="file_public_id",
            name="notafile.txt",
            name_in_bucket="testtesttest.txt",
            subpath="subpath",
            size_original=0,  # bytes
            size_stored=0,
            compressed=False,
            public_key="test",
            salt="test",
            checksum="",
            time_uploaded=timestamp(),
            project_id=projects[0],
        )
    ]

    # files_more = [
    #     File(
    #         name="description.txt",
    #         name_in_bucket="description.txt",
    #         subpath="",
    #         size=254,
    #         project_id=projects[1],
    #         size_encrypted=0,
    #         compressed=False,
    #         public_key="test",
    #         salt="test",
    #         checksum="",
    #         time_uploaded=timestamp(),
    #     ),
    #     File(
    #         name="Sample_1/data.txt",
    #         name_in_bucket="Sample_1/data.txt",
    #         subpath="Sample_1",
    #         size=189,
    #         project_id=projects[1],
    #         size_encrypted=0,
    #         compressed=False,
    #         public_key="test",
    #         salt="test",
    #         checksum="",
    #         time_uploaded=timestamp(),
    #     ),
    #     File(
    #         name="Sample_1/source.txt",
    #         name_in_bucket="Sample_1/source.txt",
    #         subpath="Sample_1",
    #         size=754,
    #         project_id=projects[1],
    #         size_encrypted=0,
    #         compressed=False,
    #         public_key="test",
    #         salt="test",
    #         checksum="",
    #         time_uploaded=timestamp(),
    #     ),
    #     File(
    #         name="Sample_1/meta/info.txt",
    #         name_in_bucket="Sample_1/meta/info.txt",
    #         subpath="Sample_1/meta",
    #         size=65,
    #         project_id=projects[1],
    #         size_encrypted=0,
    #         compressed=False,
    #         public_key="test",
    #         salt="test",
    #         checksum="",
    #         time_uploaded=timestamp(),
    #     ),
    #     File(
    #         name="Sample_2/data.txt",
    #         name_in_bucket="Sample_2/data.txt",
    #         subpath="Sample_2",
    #         size=399,
    #         project_id=projects[1],
    #         size_encrypted=0,
    #         compressed=False,
    #         public_key="test",
    #         salt="test",
    #         checksum="",
    #         time_uploaded=timestamp(),
    #     ),
    #     File(
    #         name="Sample_2/source.txt",
    #         name_in_bucket="Sample_2/source.txt",
    #         subpath="Sample_2",
    #         size=420,
    #         project_id=projects[1],
    #         size_encrypted=0,
    #         compressed=False,
    #         public_key="test",
    #         salt="test",
    #         checksum="",
    #         time_uploaded=timestamp(),
    #     ),
    #     File(
    #         name="Sample_2/meta/info.txt",
    #         name_in_bucket="Sample_2/meta/info.txt",
    #         subpath="Sample_2/meta",
    #         size=241,
    #         project_id=projects[1],
    #         size_encrypted=0,
    #         compressed=False,
    #         public_key="test",
    #         salt="test",
    #         checksum="",
    #         time_uploaded=timestamp(),
    #     ),
    #     File(
    #         name="sample_list.txt",
    #         name_in_bucket="sample_list.txt",
    #         subpath="",
    #         size=97,
    #         project_id=projects[1],
    #         size_encrypted=0,
    #         compressed=False,
    #         public_key="test",
    #         salt="test",
    #         checksum="",
    #         time_uploaded=timestamp(),
    #     ),
    #     File(
    #         name="Plates/Sample_1/layout.txt",
    #         name_in_bucket="Sample_1/layout.txt",
    #         subpath="Plates/Sample_1",
    #         size=136,
    #         project_id=projects[1],
    #         size_encrypted=0,
    #         compressed=False,
    #         public_key="test",
    #         salt="test",
    #         checksum="",
    #         time_uploaded=timestamp(),
    #     ),
    #     File(
    #         name="Plates/Sample_2/layout.txt",
    #         name_in_bucket="Sample_2/layout.txt",
    #         subpath="Plates/Sample_2",
    #         size=125,
    #         project_id=projects[1],
    #         size_encrypted=0,
    #         compressed=False,
    #         public_key="test",
    #         salt="test",
    #         checksum="",
    #         time_uploaded=timestamp(),
    #     ),
    # ]

    # Foreign key/relationship updates
    for p in projects:
        for u in users:
            u.projects.append(p)

    for u in users:
        if u.facility_id:
            facilities[0].users.append(u)

    for f in files:
        projects[0].files.append(f)

    for p in projects:
        facilities[0].projects.append(p)
    # for x in projects:
    #     users[0].facility_projects.append(x)
    # for ind in [1, 3, 4, 6, 9]:
    #     users[1].user_projects.append(projects[ind])
    # for ind in [2, 5, 7, 8, 10]:
    #     users[3].user_projects.append(projects[ind])

    # for x in projects:
    #     facilities[0].facility_projects.append(x)
    # for ind in [1, 2, 3, 4, 5]:
    #     facilities[1].fac_projects.append(projects[ind])
    # for ind in [6, 7, 8, 9, 10]:
    #     facilities[2].fac_projects.append(projects[ind])

    # for fl in files:
    #     projects[0].project_files.append(fl)
    # for prj in projects[1:]:
    #     if prj.status == "Delivered":
    #         create_files_for_project(prj)

    # for fl in files_more:
    #     projects[1].project_files.append(fl)

    # Add user and facility, the rest is automatically added and commited

    db.session.add_all(facilities)
    db.session.add_all(projects)
    db.session.add_all(users)
    db.session.add_all(files)

    # Required for change in db
    db.session.commit()
