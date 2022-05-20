from dds_web import fill_db_wrapper
import os

def test_fill_db_wrapper(client):
    """"""
    os.system("init-db production")