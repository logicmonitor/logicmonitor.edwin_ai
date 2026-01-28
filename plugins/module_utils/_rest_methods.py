#!/usr/bin/env python
# -*- coding: utf-8 -*-

# NOTE: FOR INTERNAL USE ONLY.

# see https://docs.ansible.com/projects/ansible/devel/dev_guide/testing/sanity/import.html
IMPORT_ERRORS = []
try:
    import requests
except ImportError as ie:
    IMPORT_ERRORS.append(ie)


def get_auth_token(portal: str, access_id: str, access_key: str) -> str:
    _validate_imports()

    payload = {
        'grant_type': 'client_credentials',
        'client_id': access_id,
        'client_secret': access_key
    }
    response = requests.post(f"https://{portal}.dexda.ai/auth/token", data=payload)

    # TODO error handling
    return response.json().get('access_token')


def post(url: str, access_token: str, payload: str):
    _validate_imports()

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}
    response = requests.post(url, data=payload, headers=headers)

    # TODO error handling
    return response


def _validate_imports() -> None:
    for ex in IMPORT_ERRORS:
        raise ex
