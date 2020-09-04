"JSON schemas for the API."

import flask

from code_dds import constants


_USERNAME = {"type": "string", "pattern": "^[a-zA-Z][a-zA-Z0-9_-]*$"}
_URI      = {"type": "string", "format": "uri"}
_IUID     = {"type": "string", "pattern": "^[a-f0-9]{32}$"}
_DATETIME = {"type": "string", "format": "date-time"}

ROOT = {
    "$schema": constants.JSON_SCHEMA_URL,
    "type": "object",
    "properties": {
        "$id": _URI,
        "timestamp": _DATETIME
    },
    "required": [
        "$id",
        "timestamp"
    ]
}

LOGS = {
    "$schema": constants.JSON_SCHEMA_URL,
    "type": "object",
    "properties": {
        "$id": _URI,
        "timestamp": _DATETIME,
        "doc": {
            "type": "object",
            "properties": {
                "iuid": _IUID,
                "href": _URI
            },
            "required": [
                "iuid",
                "href"
            ],
            "additionalProperties": False
        },
        "logs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "added": {"type": "array"},
                    "updated": {"type": "object"},
                    "removed": {"type": "object"},
                    "timestamp": _DATETIME,
                    "username": {"type": ["string", "null"]},
                    "remote_addr": {"type": ["string", "null"]},
                    "user_agentr": {"type": ["string", "null"]}
                },
                "required": [
                    "added",
                    "updated",
                    "removed",
                    "timestamp",
                    "username",
                    "remote_addr",
                    "user_agentr"
                ],
                "additionalProperties": False
            }
        }
    }
}

ABOUT_SOFTWARE = {
    "$schema": constants.JSON_SCHEMA_URL,
    "type": "object",
    "properties": {
        "$id": _URI,
        "timestamp": _DATETIME,
        "software": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "version": {"type": "string"},
                    "href": _URI
                }
            }
        }
    },
    "required": [
        "$id",
        "timestamp",
        "software"
    ],
    "additionalProperties": False
}

USER = {
    "$schema": constants.JSON_SCHEMA_URL,
    "type": "object",
    "properties": {
        "$id": _URI,
        "timestamp": _DATETIME,
        "iuid": _IUID,
        "username": _USERNAME,
        "email": {"type": "string", "format": "email"},
        "role": {"type": "string", "enum": ["admin", "user"]},
        "status": {"type": "string", "enum": ["pending", "enabled", "disabled"]},
        "created": _DATETIME,
        "modified": _DATETIME,
        "logs": {
            "type": "object",
            "properties": {
                "href": _URI
            },
            "required": ["href"],
            "additionalProperties": False
        }
    },
    "required": [
        "$id",
        "timestamp",
        "iuid",
        "username",
        "email",
        "role",
        "status",
        "created",
        "modified",
        "logs"
    ],
    "additionalProperties": False
}

USERS = {
    "$schema": constants.JSON_SCHEMA_URL,
    "type": "object",
    "properties": {
        "$id": _URI,
        "timestamp": _DATETIME,
        "users": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "username": _USERNAME,
                    "href": _URI
                },
                "required": ["username", "href"],
                "additionalProperties": False
            }
        }
    },
    "required": [
        "$id",
        "timestamp",
        "users"
    ],
    "additionalProperties": False
}

blueprint = flask.Blueprint("api_schema", __name__)

@blueprint.route("/root")
def root():
    return flask.jsonify(ROOT)

@blueprint.route("/logs")
def logs():
    return flask.jsonify(LOGS)

@blueprint.route("/about/software")
def about_software():
    return flask.jsonify(ABOUT_SOFTWARE)

@blueprint.route("/user")
def user():
    return flask.jsonify(USER)

@blueprint.route("/users")
def users():
    return flask.jsonify(USERS)
