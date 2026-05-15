#!/usr/bin/env python
# -*- coding: utf-8 -*-

# NOTE: FOR INTERNAL USE ONLY.

import re

# see https://docs.ansible.com/projects/ansible/devel/dev_guide/testing/sanity/import.html
IMPORT_ERRORS = []
try:
    import requests
except ImportError as ie:
    IMPORT_ERRORS.append(ie)

_VALID_PORTAL = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,62}$")


def _validate_portal(portal: str) -> str:
    if not _VALID_PORTAL.match(portal):
        raise ValueError(
            "Invalid portal name. "
            "Must be alphanumeric with hyphens/dots/underscores."
        )
    return portal


def get_auth_token(portal: str, access_id: str, access_key: str) -> str:
    _validate_imports()

    portal = _validate_portal(portal)
    payload = {
        'grant_type': 'client_credentials',
        'client_id': access_id,
        'client_secret': access_key
    }
    response = requests.post(
        f"https://{portal}.dexda.ai/auth/token",
        data=payload,
        timeout=30,
        verify=True,
    )
    response.raise_for_status()
    return response.json().get('access_token')


def post(url: str, access_token: str, payload: str):
    _validate_imports()

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}
    response = requests.post(
        url,
        data=payload,
        headers=headers,
        timeout=30,
        verify=True,
    )
    return response


def _validate_imports() -> None:
    for ex in IMPORT_ERRORS:
        raise ex
