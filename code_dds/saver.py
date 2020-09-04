"Base entity saver context class."

import copy
import json

import flask

from code_dds import constants
from code_dds import utils


class BaseSaver:
    "Base entity saver context."

    DOCTYPE = None
    HIDDEN_FIELDS = []

    def __init__(self, doc=None):
        if doc is None:
            self.original = {}
            self.doc = {"iuid": utils.get_iuid(),
                        "created": utils.get_time()}
            self.initialize()
        else:
            self.original = copy.deepcopy(doc)
            self.doc = doc
        self.prepare()

    def __enter__(self):
        return self

    def __exit__(self, etyp, einst, etb):
        if etyp is not None:
            return False
        self.finalize()
        self.doc["modified"] = utils.get_time()
        self.upsert()
        self.add_log()

    def __getitem__(self, key):
        return self.doc[key]

    def __setitem__(self, key, value):
        self.doc[key] = value

    def initialize(self):
        "Initialize the new entity."
        pass

    def prepare(self):
        "Preparations before making any changes."
        pass

    def finalize(self):
        "Final operations and checks on the entity."
        pass

    def upsert(self):
        "Actually insert or update the entity in the database."
        raise NotImplementedError

    def add_log(self):
        """Add a log entry recording the the difference betweens the current
        and the original entity, hiding values of specified keys.
        'added': list of keys for items added in the current.
        'updated': dictionary of items updated; original values.
        'removed': dictionary of items removed; original values.
        """
        added = list(set(self.doc).difference(self.original or {}))
        updated = dict([(k, self.original[k])
                        for k in set(self.doc).intersection(self.original or {})
                        if self.doc[k] != self.original[k]])
        removed = dict([(k, self.original[k])
                        for k in set(self.original or {}).difference(self.doc)])
        for key in ["iuid", "modified"]:
            try:
                added.remove(key)
            except ValueError:
                pass
        updated.pop("modified", None)
        for key in self.HIDDEN_FIELDS:
            if key in updated:
                updated[key] = "***"
            if key in removed:
                removed[key] = "***"
        values = [utils.get_iuid(),
                  self.doc["iuid"],
                  json.dumps(added),
                  json.dumps(updated),
                  json.dumps(removed),
                  utils.get_time()]
        if hasattr(flask.g, "current_user") and flask.g.current_user:
            values.append(flask.g.current_user["username"])
        else:
            values.append(None)
        if flask.has_request_context():
            values.append(str(flask.request.remote_addr))
            values.append(str(flask.request.user_agent))
        else:
            values.append(None)
            values.append(None)
        with flask.g.db:
            flask.g.db.execute("INSERT INTO logs "
                               " ('iuid', 'docid',"
                               "  'added', 'updated', 'removed',"
                               "  'timestamp', 'username',"
                               " 'remote_addr', 'user_agent')"
                               " VALUES (?,?,?,?,?,?,?,?,?)", values)
