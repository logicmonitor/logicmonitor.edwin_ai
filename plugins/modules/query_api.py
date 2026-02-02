#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2026 LogicMonitor, Inc.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.logicmonitor.edwin_ai.plugins.module_utils.rest_methods import get_auth_token
from ansible_collections.logicmonitor.edwin_ai.plugins.module_utils.rest_methods import post

import json
import time

DOCUMENTATION = r"""
---
module: query_api
short_description: Edwin Query API
description:
    - Provides operations against EdwinAI's query API.
version_added: "0.1.0"
author:
    - stair (@stair-lm)

extends_documentation_fragment:
    - logicmonitor.edwin_ai.auth
    - logicmonitor.edwin_ai.portal

requirements:
    - Python 'requests' package
    - An EdwinAI portal
    - EdwinAI API credentials that have `query_records` permissions

options:
    record_type:
        description:
            - Record type to retrieve from Edwin.
        required: true
        type: str
        choices:
            - alerts
            - events
            - insights
    fields:
        description:
            - Field(s) to return from the API.
            - If not provided, all fields will be returned.
        type: list
        default: []
    limit:
        description:
            - Maximum number of records to retrieve.
        type: int
        default: 5
    lookback_window:
        description:
            - Constrains results to the time period of `[now - lookback_window, now]`.
            - This variable is measured in seconds.
            - Default value is 24hrs (i.e., 86,400 seconds).
        type: int
        default: 86400
"""

EXAMPLES = r"""
- name: Retrieve alerts using an API token from a vault
  hosts: localhost
  vars_files:
    - vault.yml
  tasks:
    - name: Retrieve alerts for portal 'foo'
      logicmonitor.edwin_ai.insights:
        access_id: "{{ edwin_access_id }}"
        access_key: "{{ edwin_access_key }}"
        portal: foo
        record_type: alerts
"""

RETURN = r"""
changed:
    description: Indicates whether a change was affected against the server
    returned: always
    type: bool
    sample: false
data:
    description:
        - Results and query metadata.
        - The nested 'results' element is an ordered list of records.
    returned: success
    type: dict
    sample: { "meta": { "count": 123, "recordType": "alerts" }, "results": [...] }
failed:
    description: Indicates whether the query failed (e.g., HTTP 5xx or 4xx errors)
    returned: always
    type: bool
    sample: false
"""


def main():
    module = AnsibleModule(
        argument_spec=dict(
            # required
            access_id=dict(required=True, type="str"),
            access_key=dict(required=True, type="str", no_log=True),
            portal=dict(required=True, type="str"),
            record_type=dict(required=True, type="str", choices=['alerts', 'events', 'insights']),

            # optional
            fields=dict(type="list", default=[]),
            limit=dict(type="int", default=5),
            lookback_window=dict(type="int", default=86_400)
        ),
    )

    json = _query(module)
    module.exit_json(data=json)


def _query(module: AnsibleModule) -> str:
    p = module.params

    portal = p['portal']
    endpoint = f"https://{portal}.dexda.ai/ui/query/records"
    # TODO cache token (and support expiry)
    bearer_token = get_auth_token(portal, p['access_id'], p['access_key'])

    request = _create_request(module)
    response = post(endpoint, bearer_token, json.dumps(request))

    # TODO error handling
    return response.json()


def _create_request(module: AnsibleModule) -> dict:
    p = module.params

    request = {
        "env": {
            "timezone": "Europe/London"
        },
        "fields": p['fields'],
        "recordType": p['record_type'],
        "size": p['limit'],
    }

    # request will be constrained to `[now - lookback, now]`
    now = time.time()
    start_epoch = int((now - p['lookback_window']) * 1_000)

    match p['record_type']:
        case 'alerts':
            epoch_field = 'meta.createdTimestamp'
            request['filter'] = _create_filter('cf.eventSeverity', epoch_field, start_epoch)
            request['order'] = _create_order(epoch_field)
        case 'events':
            epoch_field = 'meta.eventTimestamp'
            request['filter'] = _create_filter('cf.eventSeverity', epoch_field, start_epoch)
            request['order'] = _create_order(epoch_field)
        case 'insights':
            epoch_field = 'meta.createdTimestamp'
            request['filter'] = _create_filter('ml.highestSeverity', epoch_field, start_epoch)
            request['order'] = _create_order(epoch_field)

    return request


def _create_filter(severity_field: str, epoch_field: str, epoch_value: long) -> dict:
    return {
        "expression": {
            "AND": [
                {
                    "GREATER_THAN_EQUAL": [
                        {
                            "field": severity_field,
                            "type": "integer"
                        },
                        4
                    ],
                },
                {
                    "GREATER_THAN_EQUAL": [
                        {
                            "field": epoch_field,
                            "type": "long"
                        },
                        epoch_value
                    ],
                },
            ]
        },
        "schemaName": "filterCondition",
        "schemaVersion": "4",
    }


def _create_order(epoch_field: str) -> list:
    return [
        {
           "type": "desc",
           "field": epoch_field
        },
   ]


if __name__ == "__main__":
    main()
