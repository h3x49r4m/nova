#!/usr/bin/env python3
"""
Placeholder migration file for team-pipeline-auto-review v1.0.0
This file exists for migration system compatibility.
Future migrations can be added here.
"""

def migrate(state: dict) -> dict:
    """
    Placeholder migration function.
    No migration needed for initial version.
    """
    import copy
    return copy.deepcopy(state)


def validate(state: dict) -> tuple[bool, list[str]]:
    """
    Validate that state is compatible with v1.0.0.
    """
    errors = []

    if 'review_type' not in state:
        errors.append("Missing required field: review_type")

    if 'status' not in state:
        errors.append("Missing required field: status")

    if 'checks' not in state:
        errors.append("Missing required field: checks")

    return (len(errors) == 0, errors)
