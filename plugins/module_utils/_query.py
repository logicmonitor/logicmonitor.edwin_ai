#!/usr/bin/env python
# -*- coding: utf-8 -*-

# NOTE: FOR INTERNAL USE ONLY.

# Shared helpers for building Edwin AI `/ui/query/records` request bodies.
# Used by both the `query_api` module and the `alerts` EDA event source so the
# filter/order construction stays DRY.


def create_filter(
    severity_field: str,
    epoch_field: str,
    epoch_value: int,
    severity_threshold: int = 4,
) -> dict:
    """Build a `filterCondition` expression for the query API.

    Constrains results to records whose ``severity_field`` is at least
    ``severity_threshold`` and whose ``epoch_field`` is at or after
    ``epoch_value`` (epoch milliseconds).
    """
    return {
        "expression": {
            "AND": [
                {
                    "GREATER_THAN_EQUAL": [
                        {
                            "field": severity_field,
                            "type": "integer"
                        },
                        severity_threshold
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


def create_order(epoch_field: str) -> list:
    """Build a descending order clause on ``epoch_field``."""
    return [
        {
            "type": "desc",
            "field": epoch_field
        },
    ]
