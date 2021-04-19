"""USED ONLY DURING DEVELOPMENT! Adds test data to the database."""

import os
import uuid

from code_dds.db_code.models import User, Project, Facility, File, Role
from code_dds import db
from code_dds import timestamp


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
#                  date_uploaded='2020-05-25', project_id=project
#                  )
#     project.project_files.append(mfile)


def fill_db():
    """Fills the database with initial entries used for development."""

    users = [
        User(
            public_id="public_user_id",
            username="username",
            password="$argon2id$v=19$m=102400,t=2,p=8$0jcemW3Ln+HTPUt/E3xtKQ$aZGqrrBBU5gq5TbWYwUWD62UiQUmTksbKOkmbMJzdhs",
            admin=False,
        )
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
    ]

    facilities = [
        Facility(public_id="public_facility_id",
                 username="facility",
                 password="$argon2id$v=19$m=102400,t=2,p=8$mgkOMH/4B16suy5TMw+4KQ$7j5eT0zMOmdUj2q1A+dcgC9TM4QOl39GeHWdYh+QdEE",
                 name="Facility 1",
                 safespring="redacted")
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
    ]

    projects = [
        Project(
            id="ProjectID",
            title="project_title",
            category="Category",
            date_created=timestamp(),
            date_updated=timestamp(),
            status="Ongoing",
            pi="PI",
            owner=users[0],
            facility=facilities[0],
            size=7357,
            bucket=f"ProjectID_202121185120157665_{str(uuid.uuid4())}",
            public_key="D92950F6755889FA22408B328B733ACD2242BCE570292540564AEC6E7A1B2626",
            private_key="78C784A9E6A3745E23E8199EB0310884A0696FC9A999EFE24889686C5815F073",
            description="This is a test project",
            delivery_option="S3",
            sensitive=True
        ),
        Project(
            id="ProjectID_2",
            title="project_title_2",
            category="Category_2",
            date_created=timestamp(),
            date_updated=timestamp(),
            status="Ongoing",
            pi="PI_2",
            owner=users[0],
            facility=facilities[0],
            size=7357,
            bucket=f"ProjectID_2_202121185120157665_{str(uuid.uuid4())}",
            public_key="D92950F6755889FA22408B328B733ACD2242BCE570292540564AEC6E7A1B2626",
            private_key="78C784A9E6A3745E23E8199EB0310884A0696FC9A999EFE24889686C5815F073",
            description="This is a test project",
            delivery_option="S3",
            sensitive=True
        )
        # Project(id="ff27977db6f5334dd055eefad2248d61", title="Project1",
        #         category="Category1",
        #         order_date=timestamp(), delivery_date=None,
        #         status="Ongoing", sensitive=True, description="test",
        #         pi="", owner=users[0], facility=facilities[0], size=0,
        #         size_enc=0, delivery_option="S3",
        #         public_key=("092C894633C31C3EF9E90A3EF2400E4AC4D2ADE8BF"
        #                     "7EFECAB889829253136B33"),
        #         private_key=("83B7C905A0C7AA9B95456440CBC80956CB53CABF19AE76B01A"
        #                      "A5F7324FFA74CBAC1350DDF760BFDBDF94CD6314D3F7418E37"
        #                      "064954751F7320B9CE83E1DDCE1CB1412564C536E3221D07F3"
        #                      "A1BE27E07B9694061DADBD2B581E0AB0D8"),
        #         salt="9A2694986A488E438DA998E73E93E9C4",
        #         nonce="D55240DB506C2C22CF248F18",
        #         passphrase="922d5b93f5455050e96b33a45f65a3e8c7d4f6198ed8473879c11e10711ed937"),
        # Project(id="GEN001", title="RNA-seq study",
        #         category="Genomics",
        #         order_date="2020-06-27", delivery_date="2020-08-19",
        #         status="Delivered", sensitive=True,
        #         description="RNA-seq study on rats",
        #         pi="", owner=users[1], facility=facilities[1], size=40000000000,
        #         size_enc=25000000000, delivery_option="DC_DDS",
        #         public_key=("092C894633C31C3EF9E90A3EF2400E4AC4D2ADE8BF"
        #                     "7EFECAB889829253136B33"),
        #         private_key=("83B7C905A0C7AA9B95456440CBC80956CB53CABF19AE76B01A"
        #                      "A5F7324FFA74CBAC1350DDF760BFDBDF94CD6314D3F7418E37"
        #                      "064954751F7320B9CE83E1DDCE1CB1412564C536E3221D07F3"
        #                      "A1BE27E07B9694061DADBD2B581E0AB0D8"),
        #         salt="9A2694986A488E438DA998E73E93E9C4",
        #         nonce="D55240DB506C2C22CF248F18",
        #         passphrase="922d5b93f5455050e96b33a45f65a3e8c7d4f6198ed8473879c11e10711ed937"
        #         ),
        # Project(id="GEN002", title="Whole genome reseq",
        #         category="Genomics",
        #         order_date="2020-07-14", delivery_date="2020-10-09",
        #         status="Delivered", sensitive=True,
        #         description="Human whole genome requencing study",
        #         pi="", owner=users[3], facility=facilities[1], size=150000000000,
        #         size_enc=110000000000, delivery_option="DC_DDS",
        #         public_key=("092C894633C31C3EF9E90A3EF2400E4AC4D2ADE8BF"
        #                     "7EFECAB889829253136B33"),
        #         private_key=("83B7C905A0C7AA9B95456440CBC80956CB53CABF19AE76B01A"
        #                      "A5F7324FFA74CBAC1350DDF760BFDBDF94CD6314D3F7418E37"
        #                      "064954751F7320B9CE83E1DDCE1CB1412564C536E3221D07F3"
        #                      "A1BE27E07B9694061DADBD2B581E0AB0D8"),
        #         salt="9A2694986A488E438DA998E73E93E9C4",
        #         nonce="D55240DB506C2C22CF248F18",
        #         passphrase="922d5b93f5455050e96b33a45f65a3e8c7d4f6198ed8473879c11e10711ed937"),
        # Project(id="GEN003", title="Interspecific gene flow",
        #         category="Genomics",
        #         order_date="2020-09-18", delivery_date="2019-10-12",
        #         status="Delivered", sensitive=False,
        #         description="Evolution of specialisation in black and white rhinocereos",
        #         pi="", owner=users[1], facility=facilities[1], size=2385738910,
        #         size_enc=1678434812, delivery_option="DC_DDS",
        #         public_key=("092C894633C31C3EF9E90A3EF2400E4AC4D2ADE8BF"
        #                     "7EFECAB889829253136B33"),
        #         private_key=("83B7C905A0C7AA9B95456440CBC80956CB53CABF19AE76B01A"
        #                      "A5F7324FFA74CBAC1350DDF760BFDBDF94CD6314D3F7418E37"
        #                      "064954751F7320B9CE83E1DDCE1CB1412564C536E3221D07F3"
        #                      "A1BE27E07B9694061DADBD2B581E0AB0D8"),
        #         salt="9A2694986A488E438DA998E73E93E9C4",
        #         nonce="D55240DB506C2C22CF248F18",
        #         passphrase="922d5b93f5455050e96b33a45f65a3e8c7d4f6198ed8473879c11e10711ed937"),
        # Project(id="GEN004", title="Corona expression study",
        #         category="Genomics",
        #         order_date="2020-10-10", delivery_date=None,
        #         status="Ongoing", sensitive=True,
        #         description="Gene expressions of corono viurs",
        #         pi="", owner=users[1], facility=facilities[1], size=0,
        #         size_enc=0, delivery_option="DC_DDS",
        #         public_key=("092C894633C31C3EF9E90A3EF2400E4AC4D2ADE8BF"
        #                     "7EFECAB889829253136B33"),
        #         private_key=("83B7C905A0C7AA9B95456440CBC80956CB53CABF19AE76B01A"
        #                      "A5F7324FFA74CBAC1350DDF760BFDBDF94CD6314D3F7418E37"
        #                      "064954751F7320B9CE83E1DDCE1CB1412564C536E3221D07F3"
        #                      "A1BE27E07B9694061DADBD2B581E0AB0D8"),
        #         salt="9A2694986A488E438DA998E73E93E9C4",
        #         nonce="D55240DB506C2C22CF248F18",
        #         passphrase="922d5b93f5455050e96b33a45f65a3e8c7d4f6198ed8473879c11e10711ed937"),
        # Project(id="GEN005", title="Gastric microbiota",
        #         category="Genomics",
        #         order_date="2020-10-27", delivery_date=None,
        #         status="Ongoing", sensitive=False,
        #         description="General population and their associations with gastric lessons",
        #         pi="", owner=users[3], facility=facilities[1], size=0,
        #         size_enc=0, delivery_option="DC_DDS",
        #         public_key=("092C894633C31C3EF9E90A3EF2400E4AC4D2ADE8BF"
        #                     "7EFECAB889829253136B33"),
        #         private_key=("83B7C905A0C7AA9B95456440CBC80956CB53CABF19AE76B01A"
        #                      "A5F7324FFA74CBAC1350DDF760BFDBDF94CD6314D3F7418E37"
        #                      "064954751F7320B9CE83E1DDCE1CB1412564C536E3221D07F3"
        #                      "A1BE27E07B9694061DADBD2B581E0AB0D8"),
        #         salt="9A2694986A488E438DA998E73E93E9C4",
        #         nonce="D55240DB506C2C22CF248F18",
        #         passphrase="922d5b93f5455050e96b33a45f65a3e8c7d4f6198ed8473879c11e10711ed937"),
        # Project(id="IMG001", title="Mitochondrial translation",
        #         category="Imaging",
        #         order_date="2020-05-25", delivery_date="2020-07-12",
        #         status="Delivered", sensitive=True,
        #         description="Distinct pre-initiation steps in human translation",
        #         pi="", owner=users[1], facility=facilities[2], size=8700000000,
        #         size_enc=2900000000, delivery_option="DC_DDS",
        #         public_key=("092C894633C31C3EF9E90A3EF2400E4AC4D2ADE8BF"
        #                     "7EFECAB889829253136B33"),
        #         private_key=("83B7C905A0C7AA9B95456440CBC80956CB53CABF19AE76B01A"
        #                      "A5F7324FFA74CBAC1350DDF760BFDBDF94CD6314D3F7418E37"
        #                      "064954751F7320B9CE83E1DDCE1CB1412564C536E3221D07F3"
        #                      "A1BE27E07B9694061DADBD2B581E0AB0D8"),
        #         salt="9A2694986A488E438DA998E73E93E9C4",
        #         nonce="D55240DB506C2C22CF248F18",
        #         passphrase="922d5b93f5455050e96b33a45f65a3e8c7d4f6198ed8473879c11e10711ed937"),
        # Project(id="IMG002", title="DNA polymerases",
        #         category="Imaging",
        #         order_date="2020-06-18", delivery_date="2020-08-25",
        #         status="Delivered", sensitive=True,
        #         description="Structural basis for the increased processivity of D-family DNA polytmerases",
        #         pi="", owner=users[3], facility=facilities[2], size=55000000000,
        #         size_enc=32000000000, delivery_option="DC_DDS",
        #         public_key=("092C894633C31C3EF9E90A3EF2400E4AC4D2ADE8BF"
        #                     "7EFECAB889829253136B33"),
        #         private_key=("83B7C905A0C7AA9B95456440CBC80956CB53CABF19AE76B01A"
        #                      "A5F7324FFA74CBAC1350DDF760BFDBDF94CD6314D3F7418E37"
        #                      "064954751F7320B9CE83E1DDCE1CB1412564C536E3221D07F3"
        #                      "A1BE27E07B9694061DADBD2B581E0AB0D8"),
        #         salt="9A2694986A488E438DA998E73E93E9C4",
        #         nonce="D55240DB506C2C22CF248F18",
        #         passphrase="922d5b93f5455050e96b33a45f65a3e8c7d4f6198ed8473879c11e10711ed937"),
        # Project(id="IMG003", title="Type III ATP syntase",
        #         category="Imaging",
        #         order_date="2020-09-11", delivery_date="2020-10-05",
        #         status="Delivered", sensitive=True,
        #         description="Type III ATP synthase is a symmetry-deviated dimer that induces membrane",
        #         pi="", owner=users[3], facility=facilities[2], size=8700000000,
        #         size_enc=2900000000, delivery_option="DC_DDS",
        #         public_key=("092C894633C31C3EF9E90A3EF2400E4AC4D2ADE8BF"
        #                     "7EFECAB889829253136B33"),
        #         private_key=("83B7C905A0C7AA9B95456440CBC80956CB53CABF19AE76B01A"
        #                      "A5F7324FFA74CBAC1350DDF760BFDBDF94CD6314D3F7418E37"
        #                      "064954751F7320B9CE83E1DDCE1CB1412564C536E3221D07F3"
        #                      "A1BE27E07B9694061DADBD2B581E0AB0D8"),
        #         salt="9A2694986A488E438DA998E73E93E9C4",
        #         nonce="D55240DB506C2C22CF248F18",
        #         passphrase="922d5b93f5455050e96b33a45f65a3e8c7d4f6198ed8473879c11e10711ed937"),
        # Project(id="IMG004", title="Proton exchanger NHE9",
        #         category="Imaging",
        #         order_date="2020-11-09", delivery_date=None,
        #         status="Ongoing", sensitive=False,
        #         description="Distinct pre-initiation steps in human translation",
        #         pi="", owner=users[1], facility=facilities[2], size=0,
        #         size_enc=0, delivery_option="DC_DDS",
        #         public_key=("092C894633C31C3EF9E90A3EF2400E4AC4D2ADE8BF"
        #                     "7EFECAB889829253136B33"),
        #         private_key=("83B7C905A0C7AA9B95456440CBC80956CB53CABF19AE76B01A"
        #                      "A5F7324FFA74CBAC1350DDF760BFDBDF94CD6314D3F7418E37"
        #                      "064954751F7320B9CE83E1DDCE1CB1412564C536E3221D07F3"
        #                      "A1BE27E07B9694061DADBD2B581E0AB0D8"),
        #         salt="9A2694986A488E438DA998E73E93E9C4",
        #         nonce="D55240DB506C2C22CF248F18",
        #         passphrase="922d5b93f5455050e96b33a45f65a3e8c7d4f6198ed8473879c11e10711ed937"),
        # Project(id="IMG005", title="Mitochondrial translation",
        #         category="Imaging",
        #         order_date="2020-11-11", delivery_date=None,
        #         status="Ongoing", sensitive=False,
        #         description="Distinct pre-initiation steps in human translation",
        #         pi="", owner=users[3], facility=facilities[2], size=0,
        #         size_enc=0, delivery_option="DC_DDS",
        #         public_key=("092C894633C31C3EF9E90A3EF2400E4AC4D2ADE8BF"
        #                     "7EFECAB889829253136B33"),
        #         private_key=("83B7C905A0C7AA9B95456440CBC80956CB53CABF19AE76B01A"
        #                      "A5F7324FFA74CBAC1350DDF760BFDBDF94CD6314D3F7418E37"
        #                      "064954751F7320B9CE83E1DDCE1CB1412564C536E3221D07F3"
        #                      "A1BE27E07B9694061DADBD2B581E0AB0D8"),
        #         salt="9A2694986A488E438DA998E73E93E9C4",
        #         nonce="D55240DB506C2C22CF248F18",
        #         passphrase="922d5b93f5455050e96b33a45f65a3e8c7d4f6198ed8473879c11e10711ed937")
    ]

    roles = [
        Role(username=users[0].username, facility=False),
        Role(username=facilities[0].username, facility=True),
    ]

    files = [
        File(
            name="notafile.txt",
            name_in_bucket="testtesttest.txt",
            subpath="subpath",
            size=0,  # bytes
            size_encrypted=0,
            compressed=False,
            public_key="test",
            salt="test",
            checksum="",
            project_id=projects[0],
            date_uploaded=timestamp())
            ]
        
    files_more = [
        File(name= 'description.txt',
           name_in_bucket= 'description.txt',
           subpath= '',
           size=254,
           project_id=projects[1],
           size_encrypted=0,
           compressed=False,
           public_key="test",
           salt="test",
           checksum="",
           date_uploaded=timestamp()),
       
        File(name= 'Sample_1/data.txt',
            name_in_bucket= 'Sample_1/data.txt',
            subpath= 'Sample_1',
            size=189,
            project_id=projects[1],
            size_encrypted=0,
            compressed=False,
            public_key="test",
            salt="test",
            checksum="",
            date_uploaded=timestamp()),
        
        File(name= 'Sample_1/source.txt',
            name_in_bucket= 'Sample_1/source.txt',
            subpath= 'Sample_1',
            size=754,
            project_id=projects[1],
            size_encrypted=0,
            compressed=False,
            public_key="test",
            salt="test",
            checksum="",
            date_uploaded=timestamp()),
        
        File(name= 'Sample_1/meta/info.txt',
            name_in_bucket= 'Sample_1/meta/info.txt',
            subpath= 'Sample_1/meta',
            size=65,
            project_id=projects[1],
            size_encrypted=0,
            compressed=False,
            public_key="test",
            salt="test",
            checksum="",
            date_uploaded=timestamp()),
        
        File(name= 'Sample_2/data.txt',
            name_in_bucket= 'Sample_2/data.txt',
            subpath= 'Sample_2',
            size=399,
            project_id=projects[1],
            size_encrypted=0,
            compressed=False,
            public_key="test",
            salt="test",
            checksum="",
            date_uploaded=timestamp()),
        
        File(name= 'Sample_2/source.txt',
            name_in_bucket= 'Sample_2/source.txt',
            subpath= 'Sample_2',
            size=420,
            project_id=projects[1],
            size_encrypted=0,
            compressed=False,
            public_key="test",
            salt="test",
            checksum="",
            date_uploaded=timestamp()),
        
        File(name= 'Sample_2/meta/info.txt',
            name_in_bucket= 'Sample_2/meta/info.txt',
            subpath= 'Sample_2/meta',
            size=241,
            project_id=projects[1],
            size_encrypted=0,
            compressed=False,
            public_key="test",
            salt="test",
            checksum="",
            date_uploaded=timestamp()),
        
        File(name= 'sample_list.txt',
            name_in_bucket= 'sample_list.txt',
            subpath= '',
            size=97,
            project_id=projects[1],
            size_encrypted=0,
            compressed=False,
            public_key="test",
            salt="test",
            checksum="",
            date_uploaded=timestamp()),
        
        File(name= 'Plates/Sample_1/layout.txt',
            name_in_bucket= 'Sample_1/layout.txt',
            subpath= 'Plates/Sample_1',
            size=136,
            project_id=projects[1],
            size_encrypted=0,
            compressed=False,
            public_key="test",
            salt="test",
            checksum="",
            date_uploaded=timestamp()),
        
        File(name= 'Plates/Sample_2/layout.txt',
            name_in_bucket= 'Sample_2/layout.txt',
            subpath= 'Plates/Sample_2',
            size=125,
            project_id=projects[1],
            size_encrypted=0,
            compressed=False,
            public_key="test",
            salt="test",
            checksum="",
            date_uploaded=timestamp())
    ]
    
    # Foreign key/relationship updates
    for x in projects:
        users[0].user_projects.append(x)
    # for ind in [1, 3, 4, 6, 9]:
    #     users[1].user_projects.append(projects[ind])
    # for ind in [2, 5, 7, 8, 10]:
    #     users[3].user_projects.append(projects[ind])

    for x in projects:
        facilities[0].user_projects.append(x)
    # for ind in [1, 2, 3, 4, 5]:
    #     facilities[1].fac_projects.append(projects[ind])
    # for ind in [6, 7, 8, 9, 10]:
    #     facilities[2].fac_projects.append(projects[ind])

    for fl in files:
        projects[0].project_files.append(fl)
    # for prj in projects[1:]:
    #     if prj.status == "Delivered":
    #         create_files_for_project(prj)
    
    for fl in files_more:
        projects[1].project_files.append(fl)

    # Add user and facility, the rest is automatically added and commited
    db.session.add_all(users)
    db.session.add_all(facilities)
    db.session.add_all(roles)
    db.session.add_all(projects)

    # Required for change in db
    db.session.commit()
