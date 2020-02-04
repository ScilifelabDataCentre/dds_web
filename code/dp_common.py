#!/usr/bin/env python3
"""Common functions in both WI and CLI"""

# IMPORTS ########################################################### IMPORTS #

import datetime
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.backends import default_backend

import base
from base import BaseHandler

# FUNCTIONS ####################################################### FUNCTIONS #


def gen_hmac(filepath: str) -> str:
    """Generates HMAC"""

    key = b"ThisIsTheSuperSecureKeyThatWillBeGeneratedLater"
    h = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())

    with open(filepath, 'rb') as f:
        for compressed_chunk in iter(lambda: f.read(16384), b''):
            h.update(compressed_chunk)
        return h.finalize()


def get_current_time() -> str:
    """Gets the current time and formats for database."""

    now = datetime.datetime.now()
    timestamp = ""
    sep = ""

    for t in (now.year, "-", now.month, "-", now.day, " ",
              now.hour, ":", now.minute, ":", now.second):
        if len(str(t)) == 1 and isinstance(t, int):
            timestamp += f"0{t}"
        else:
            timestamp += f"{t}"

    return timestamp
