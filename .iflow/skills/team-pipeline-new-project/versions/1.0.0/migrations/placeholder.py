#!/usr/bin/env python3
"""
Placeholder migration file for team-pipeline-new-project v1.0.0
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

    if 'project_name' not in state:
        errors.append("Missing required field: project_name")

    if 'status' not in state:
        errors.append("Missing required field: status")

    if 'phases' not in state:
        errors.append("Missing required field: phases")

    return (len(errors) == 0, errors)
