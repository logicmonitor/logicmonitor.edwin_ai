#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests


def get_auth_token(portal: str, access_id: str, access_key: str) -> str:
    payload = {
        'grant_type': 'client_credentials',
        'client_id': access_id,
        'client_secret': access_key
    }
    response = requests.post(f"https://{portal}.dexda.ai/auth/token", data=payload)

    # TODO error handling
    print('Response Status:', response.status_code)
#     print('Response Body:', json.dumps(response.json(), indent=2))
    return response.json().get('access_token')


def post(url: str, access_token: str, payload: str) -> Response:
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}
    response = requests.post(url, data=payload, headers=headers)

    # TODO error handling
    print('Response Status:', response.status_code)
    return response
