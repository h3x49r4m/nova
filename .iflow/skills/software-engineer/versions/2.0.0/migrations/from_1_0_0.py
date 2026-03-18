#!/usr/bin/env python3
"""
Migration script from software-engineer v1.0.0 to v2.0.0
Handles upgrade of skill version with expanded capabilities.
"""

def migrate(state: dict) -> dict:
    """
    Migrate workflow state from v1.0.0 to v2.0.0.

    This migration:
    - Updates skill version in state
    - Adds new domain flags
    - Preserves existing backend/frontend configurations
    - Adds default ML/graphics configurations
    """
    import copy

    # Create a copy to avoid modifying original
    new_state = copy.deepcopy(state)

    # Update skill version
    if 'skills_used' in new_state:
        new_state['skills_used']['software-engineer'] = '2.0.0'

    # Add new domain configurations if not present
    if 'domains' not in new_state:
        new_state['domains'] = {}

    # Ensure backend and frontend domains are preserved
    if 'backend' not in new_state['domains']:
        new_state['domains']['backend'] = {
            'enabled': True,
            'apis': ['rest', 'graphql'],
            'databases': ['postgresql', 'mysql']
        }

    if 'frontend' not in new_state['domains']:
        new_state['domains']['frontend'] = {
            'enabled': True,
            'frameworks': ['react', 'vue'],
            'styling': ['css', 'tailwind']
        }

    # Add new domains (disabled by default for backward compatibility)
    new_state['domains']['graphics'] = {
        'enabled': False,
        'apis': [],
        'libraries': []
    }

    new_state['domains']['ml'] = {
        'enabled': False,
        'frameworks': [],
        'tasks': []
    }

    new_state['domains']['data'] = {
        'enabled': False,
        'libraries': [],
        'processing': []
    }

    # Add migration metadata
    if 'migrations' not in new_state:
        new_state['migrations'] = []

    new_state['migrations'].append({
        'from': '1.0.0',
        'to': '2.0.0',
        'timestamp': '2026-02-27T00:00:00Z',
        'description': 'Upgraded software-engineer to v2.0.0 with expanded capabilities'
    })

    return new_state


def rollback(state: dict) -> dict:
    """
    Rollback from v2.0.0 to v1.0.0.

    This rollback:
    - Downgrades skill version
    - Removes ML/graphics domain configurations
    - Preserves backend/frontend configurations
    """
    import copy

    # Create a copy to avoid modifying original
    new_state = copy.deepcopy(state)

    # Downgrade skill version
    if 'skills_used' in new_state:
        new_state['skills_used']['software-engineer'] = '1.0.0'

    # Remove new domains
    if 'domains' in new_state:
        new_state['domains'].pop('graphics', None)
        new_state['domains'].pop('ml', None)
        new_state['domains'].pop('data', None)

    # Add rollback metadata
    if 'migrations' not in new_state:
        new_state['migrations'] = []

    new_state['migrations'].append({
        'from': '2.0.0',
        'to': '1.0.0',
        'timestamp': '2026-02-27T00:00:00Z',
        'description': 'Rolled back software-engineer to v1.0.0'
    })

    return new_state


def validate(state: dict) -> tuple[bool, list[str]]:
    """
    Validate that state is compatible with v2.0.0.

    Returns (is_valid, errors)
    """
    errors = []

    # Check skill version
    if 'skills_used' in state:
        skill_version = state['skills_used'].get('software-engineer')
        if skill_version != '2.0.0':
            errors.append(f"Expected software-engineer version 2.0.0, found {skill_version}")

    # Check domain structure
    if 'domains' in state:
        required_domains = ['backend', 'frontend', 'graphics', 'ml', 'data']
        for domain in required_domains:
            if domain not in state['domains']:
                errors.append(f"Missing required domain: {domain}")

    return (len(errors) == 0, errors)
