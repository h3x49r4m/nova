"""State Contract Validation Decorator.

This module provides a decorator to validate state contracts defined in SKILL.md files
at runtime, ensuring that skills honor their read/write contracts.
"""

import functools
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .exceptions import IFlowError, ValidationError, ErrorCode
from .structured_logger import StructuredLogger, LogFormat


def parse_state_contracts(skill_md_path: Path) -> Tuple[List[str], List[str]]:
    """
    Parse state contracts from a SKILL.md file.
    
    Args:
        skill_md_path: Path to the SKILL.md file
        
    Returns:
        Tuple of (read_contracts, write_contracts)
    """
    if not skill_md_path.exists():
        return [], []
    
    with open(skill_md_path, 'r') as f:
        content = f.read()
    
    read_contracts = []
    write_contracts = []
    
    # Extract Read contracts
    read_section = re.search(
        r'### Read\s*\n(.*?)(?=\n### |\n## |\Z)',
        content,
        re.DOTALL
    )
    if read_section:
        # Extract filenames from markdown list items
        matches = re.findall(r'- `([^`]+)`', read_section.group(1))
        read_contracts = matches
    
    # Extract Write contracts
    write_section = re.search(
        r'### Write\s*\n(.*?)(?=\n### |\n## |\Z)',
        content,
        re.DOTALL
    )
    if write_section:
        # Extract filenames from markdown list items
        matches = re.findall(r'- `([^`]+)`', write_section.group(1))
        write_contracts = matches
    
    return read_contracts, write_contracts


def get_shared_state_dir(project_path: Path) -> Path:
    """
    Get the shared state directory for a project.
    
    Args:
        project_path: Path to the project
        
    Returns:
        Path to the shared state directory
    """
    # Check for .state/
    state_dir = project_path / '.state'
    if state_dir.exists():
        return state_dir
    
    # Check for .iflow/skills/.shared-state/
    shared_state = project_path / '.iflow' / 'skills' / '.shared-state'
    if shared_state.exists():
        return shared_state
    
    # Default to .state/
    return state_dir


def validate_state_contracts(
    read_contracts: Optional[List[str]] = None,
    write_contracts: Optional[List[str]] = None,
    skill_md_path: Optional[Path] = None,
    logger: Optional[StructuredLogger] = None
):
    """
    Decorator to validate state contracts are honored.
    
    Args:
        read_contracts: List of state files that must exist before execution
        write_contracts: List of state files that must exist after execution
        skill_md_path: Path to SKILL.md file (will auto-parse contracts if provided)
        logger: Logger instance for validation messages
        
    Returns:
        Decorator function
        
    Example:
        @validate_state_contracts(
            read_contracts=['architecture-spec.md', 'design-spec.md'],
            write_contracts=['implementation.md', 'api-docs.md']
        )
        def implement_feature(project_path: Path):
            # Implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Determine project path (assume first argument is project_path)
            project_path = None
            if args and isinstance(args[0], Path):
                project_path = args[0]
            elif 'project_path' in kwargs:
                project_path = kwargs['project_path']
            
            if project_path is None:
                raise ValidationError(
                    message="Cannot validate state contracts: project_path not found",
                    code=ErrorCode.VALIDATION_ERROR
                )
            
            # Parse contracts from SKILL.md if provided
            if skill_md_path:
                parsed_read, parsed_write = parse_state_contracts(skill_md_path)
                if read_contracts is None:
                    read_contracts = parsed_read
                if write_contracts is None:
                    write_contracts = parsed_write
            
            # Get shared state directory
            state_dir = get_shared_state_dir(project_path)
            
            # Validate read contracts exist
            missing_read = []
            for contract in (read_contracts or []):
                contract_file = state_dir / contract
                if not contract_file.exists():
                    missing_read.append(contract)
            
            if missing_read:
                error_msg = (
                    f"State contract validation failed: {len(missing_read)} required state file(s) missing before execution\n"
                    f"Missing files: {', '.join(missing_read)}"
                )
                if logger:
                    logger.error(error_msg, extra={'missing_files': missing_read})
                raise ValidationError(
                    message=error_msg,
                    code=ErrorCode.STATE_ERROR,
                    details={'missing_read_contracts': missing_read}
                )
            
            # Record existing write contracts before execution
            existing_write = set()
            for contract in (write_contracts or []):
                contract_file = state_dir / contract
                if contract_file.exists():
                    existing_write.add(contract)
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Validate write contracts were created/updated
            missing_write = []
            for contract in (write_contracts or []):
                contract_file = state_dir / contract
                if not contract_file.exists():
                    missing_write.append(contract)
            
            if missing_write:
                warning_msg = (
                    f"State contract warning: {len(missing_write)} write contract(s) not honored\n"
                    f"Missing files: {', '.join(missing_write)}"
                )
                if logger:
                    logger.warning(warning_msg, extra={'missing_files': missing_write})
                # Don't raise exception for write contracts, just warn
                # This allows partial completion
            else:
                if logger and write_contracts:
                    logger.info(
                        f"All {len(write_contracts)} write contracts honored",
                        extra={'write_contracts': write_contracts}
                    )
            
            return result
        
        return wrapper
    return decorator


def validate_state_contract_file(
    skill_md_path: Path,
    project_path: Path,
    logger: Optional[StructuredLogger] = None
) -> Tuple[bool, List[str]]:
    """
    Validate that a skill's state contracts are satisfied.
    
    Args:
        skill_md_path: Path to the SKILL.md file
        project_path: Path to the project
        logger: Logger instance for validation messages
        
    Returns:
        Tuple of (is_valid, list of issues)
    """
    issues = []
    
    # Parse contracts
    read_contracts, write_contracts = parse_state_contracts(skill_md_path)
    
    if not read_contracts and not write_contracts:
        if logger:
            logger.info(f"No state contracts defined in {skill_md_path.name}")
        return True, []
    
    # Get shared state directory
    state_dir = get_shared_state_dir(project_path)
    
    # Validate read contracts
    for contract in read_contracts:
        contract_file = state_dir / contract
        if not contract_file.exists():
            issues.append(f"Missing read contract: {contract}")
    
    # Check write contracts (don't fail if they don't exist yet)
    for contract in write_contracts:
        contract_file = state_dir / contract
        if contract_file.exists():
            # Check if file is not empty
            if contract_file.stat().st_size == 0:
                issues.append(f"Write contract exists but is empty: {contract}")
    
    is_valid = len(issues) == 0
    
    if logger:
        if is_valid:
            logger.info(
                f"State contracts validated for {skill_md_path.name}",
                extra={
                    'read_contracts': read_contracts,
                    'write_contracts': write_contracts
                }
            )
        else:
            logger.error(
                f"State contract validation failed for {skill_md_path.name}",
                extra={'issues': issues}
            )
    
    return is_valid, issues


def get_skill_state_contracts(skill_dir: Path) -> Dict[str, List[str]]:
    """
    Get all state contracts for a skill.
    
    Args:
        skill_dir: Path to the skill directory
        
    Returns:
        Dictionary with 'read' and 'write' contract lists
    """
    skill_md_path = skill_dir / 'SKILL.md'
    
    if not skill_md_path.exists():
        return {'read': [], 'write': []}
    
    read_contracts, write_contracts = parse_state_contracts(skill_md_path)
    
    return {
        'read': read_contracts,
        'write': write_contracts
    }


def validate_all_skill_contracts(
    skills_dir: Path,
    project_path: Path,
    logger: Optional[StructuredLogger] = None
) -> Dict[str, Any]:
    """
    Validate state contracts for all skills.
    
    Args:
        skills_dir: Path to the skills directory
        project_path: Path to the project
        logger: Logger instance for validation messages
        
    Returns:
        Dictionary with validation results for all skills
    """
    results = {}
    
    if logger:
        logger.info("Starting state contract validation for all skills")
    
    # Find all SKILL.md files
    skill_md_files = list(skills_dir.glob('*/SKILL.md'))
    
    for skill_md_path in skill_md_files:
        skill_name = skill_md_path.parent.name
        is_valid, issues = validate_state_contract_file(
            skill_md_path,
            project_path,
            logger
        )
        
        results[skill_name] = {
            'is_valid': is_valid,
            'issues': issues,
            'contracts': get_skill_state_contracts(skill_md_path.parent)
        }
    
    if logger:
        valid_count = sum(1 for r in results.values() if r['is_valid'])
        total_count = len(results)
        logger.info(
            f"State contract validation complete: {valid_count}/{total_count} skills valid"
        )
    
    return results


class StateContractValidator:
    """
    Class-based state contract validator for use in skill implementations.
    """
    
    def __init__(
        self,
        skill_dir: Path,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize the state contract validator.
        
        Args:
            skill_dir: Path to the skill directory
            logger: Logger instance for validation messages
        """
        self.skill_dir = skill_dir
        self.skill_md_path = skill_dir / 'SKILL.md'
        self.logger = logger
        self.read_contracts: List[str] = []
        self.write_contracts: List[str] = []
        
        self._load_contracts()
    
    def _load_contracts(self):
        """Load state contracts from SKILL.md."""
        if self.skill_md_path.exists():
            self.read_contracts, self.write_contracts = parse_state_contracts(
                self.skill_md_path
            )
    
    def validate_read_contracts(self, project_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate that all read contracts exist.
        
        Args:
            project_path: Path to the project
            
        Returns:
            Tuple of (is_valid, list of missing contracts)
        """
        state_dir = get_shared_state_dir(project_path)
        missing = []
        
        for contract in self.read_contracts:
            contract_file = state_dir / contract
            if not contract_file.exists():
                missing.append(contract)
        
        is_valid = len(missing) == 0
        
        if self.logger:
            if is_valid:
                self.logger.info(
                    f"All read contracts validated for {self.skill_dir.name}",
                    extra={'read_contracts': self.read_contracts}
                )
            else:
                self.logger.error(
                    f"Read contracts missing for {self.skill_dir.name}",
                    extra={'missing_contracts': missing}
                )
        
        return is_valid, missing
    
    def validate_write_contracts(self, project_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate that all write contracts exist.
        
        Args:
            project_path: Path to the project
            
        Returns:
            Tuple of (is_valid, list of missing contracts)
        """
        state_dir = get_shared_state_dir(project_path)
        missing = []
        
        for contract in self.write_contracts:
            contract_file = state_dir / contract
            if not contract_file.exists():
                missing.append(contract)
        
        is_valid = len(missing) == 0
        
        if self.logger:
            if is_valid:
                self.logger.info(
                    f"All write contracts honored for {self.skill_dir.name}",
                    extra={'write_contracts': self.write_contracts}
                )
            else:
                self.logger.warning(
                    f"Write contracts not honored for {self.skill_dir.name}",
                    extra={'missing_contracts': missing}
                )
        
        return is_valid, missing
    
    def validate_all_contracts(self, project_path: Path) -> Dict[str, Any]:
        """
        Validate all state contracts.
        
        Args:
            project_path: Path to the project
            
        Returns:
            Dictionary with validation results
        """
        read_valid, read_missing = self.validate_read_contracts(project_path)
        write_valid, write_missing = self.validate_write_contracts(project_path)
        
        return {
            'is_valid': read_valid and write_valid,
            'read': {
                'is_valid': read_valid,
                'missing': read_missing,
                'contracts': self.read_contracts
            },
            'write': {
                'is_valid': write_valid,
                'missing': write_missing,
                'contracts': self.write_contracts
            }
        }
    
    def get_contracts(self) -> Dict[str, List[str]]:
        """
        Get all state contracts.
        
        Returns:
            Dictionary with 'read' and 'write' contract lists
        """
        return {
            'read': self.read_contracts,
            'write': self.write_contracts
        }
