"""Skill Invoker - Manages skill invocation and execution.

This module provides functionality for invoking skills, handling errors,
retrying failed invocations, and validating skill outputs.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import (
    SkillError
)
from .constants import Timeouts


class SkillInvocationResult:
    """Result of a skill invocation."""
    
    def __init__(
        self,
        success: bool,
        output: str,
        error: Optional[str] = None,
        exit_code: int = 0,
        execution_time: float = 0.0,
        retries: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.output = output
        self.error = error
        self.exit_code = exit_code
        self.execution_time = execution_time
        self.retries = retries
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
            "execution_time": self.execution_time,
            "retries": self.retries,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class SkillInvoker:
    """Invokes skills and manages their execution."""
    
    def __init__(
        self,
        skills_dir: Path,
        repo_root: Path,
        dry_run: bool = False,
        default_timeout: int = Timeouts.SKILL_INVOCATION.value
    ):
        self.skills_dir = skills_dir
        self.repo_root = repo_root
        self.dry_run = dry_run
        self.default_timeout = default_timeout
        
        # Skill execution history
        self.execution_history: List[SkillInvocationResult] = []
    
    def invoke_skill(
        self,
        skill_name: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        retry_on_failure: bool = True,
        max_retries: int = 3,
        validate_output: bool = True
    ) -> SkillInvocationResult:
        """Invoke a skill with the given prompt.
        
        Args:
            skill_name: Name of the skill to invoke
            prompt: Prompt to send to the skill
            context: Additional context to pass to the skill
            timeout: Execution timeout in seconds
            retry_on_failure: Whether to retry on failure
            max_retries: Maximum number of retry attempts
            validate_output: Whether to validate skill output
            
        Returns:
            SkillInvocationResult
        """
        timeout = timeout or self.default_timeout
        context = context or {}
        
        # Validate skill exists
        skill_path = self.skills_dir / skill_name
        if not skill_path.exists():
            return SkillInvocationResult(
                success=False,
                output="",
                error=f"Skill not found: {skill_name}",
                exit_code=1
            )
        
        # Load skill config
        config = self._load_skill_config(skill_path)
        if not config:
            return SkillInvocationResult(
                success=False,
                output="",
                error=f"Failed to load skill config: {skill_name}",
                exit_code=1
            )
        
        # Prepare invocation
        execution_start = time.time()
        retries = 0
        last_error = None
        
        while retries <= max_retries:
            try:
                if self.dry_run:
                    result = self._dry_run_invocation(
                        skill_name,
                        prompt,
                        context,
                        timeout
                    )
                else:
                    result = self._execute_skill(
                        skill_name,
                        prompt,
                        context,
                        timeout,
                        config
                    )
                
                execution_time = time.time() - execution_start
                
                # Validate output if requested
                if validate_output and result.success:
                    validation_result = self._validate_skill_output(
                        skill_name,
                        result.output,
                        config
                    )
                    
                    if not validation_result[0]:
                        result.success = False
                        result.error = f"Output validation failed: {validation_result[1]}"
                        result.exit_code = 1
                
                # Record execution time
                result.execution_time = execution_time
                result.retries = retries
                
                # Add to history
                self.execution_history.append(result)
                
                return result
            
            except SkillError as e:
                last_error = e.message
                retries += 1
                
                if retry_on_failure and retries <= max_retries:
                    # Exponential backoff
                    backoff_time = min(2 ** retries, 60)
                    time.sleep(backoff_time)
                else:
                    # Max retries exceeded or no retry
                    execution_time = time.time() - execution_start
                    return SkillInvocationResult(
                        success=False,
                        output="",
                        error=last_error,
                        exit_code=1,
                        execution_time=execution_time,
                        retries=retries
                    )
            
            except Exception as e:
                execution_time = time.time() - execution_start
                return SkillInvocationResult(
                    success=False,
                    output="",
                    error=f"Unexpected error: {str(e)}",
                    exit_code=1,
                    execution_time=execution_time,
                    retries=retries
                )
        
        # Should not reach here
        execution_time = time.time() - execution_start
        return SkillInvocationResult(
            success=False,
            output="",
            error=last_error or "Unknown error",
            exit_code=1,
            execution_time=execution_time,
            retries=retries
        )
    
    def _load_skill_config(self, skill_path: Path) -> Optional[Dict[str, Any]]:
        """Load skill configuration."""
        config_file = skill_path / 'config.json'
        
        if not config_file.exists():
            return None
        
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    
    def _dry_run_invocation(
        self,
        skill_name: str,
        prompt: str,
        context: Dict[str, Any],
        timeout: int
    ) -> SkillInvocationResult:
        """Simulate skill invocation for dry-run mode."""
        print(f"[DRY-RUN] Invoking skill: {skill_name}")
        print(f"[DRY-RUN] Prompt: {prompt[:100]}...")
        print(f"[DRY-RUN] Timeout: {timeout}s")
        
        return SkillInvocationResult(
            success=True,
            output=f"[DRY-RUN] Skill {skill_name} would be executed.",
            exit_code=0
        )
    
    def _execute_skill(
        self,
        skill_name: str,
        prompt: str,
        context: Dict[str, Any],
        timeout: int,
        config: Dict[str, Any]
    ) -> SkillInvocationResult:
        """Execute a skill."""
        # Prepare environment
        env = os.environ.copy()
        env['IFLOW_SKILL_NAME'] = skill_name
        env['IFLOW_REPO_ROOT'] = str(self.repo_root)
        
        # Add context as environment variables
        for key, value in context.items():
            env_key = f'IFLOW_CTX_{key.upper()}'
            env[env_key] = str(value)
        
        # Prepare command
        skill_main = self.skills_dir / skill_name / 'main.py'
        
        if skill_main.exists():
            # Python skill
            cmd = [sys.executable, str(skill_main)]
        else:
            # Use skill_cli to invoke
            skill_cli = self.skills_dir / 'skill_cli.py'
            cmd = [sys.executable, str(skill_cli), skill_name, prompt]
        
        try:
            # Execute skill
            process = subprocess.Popen(
                cmd,
                cwd=self.repo_root,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True
            )
            
            try:
                stdout, stderr = process.communicate(
                    input=prompt,
                    timeout=timeout
                )
                
                exit_code = process.returncode
                
                if exit_code == 0:
                    return SkillInvocationResult(
                        success=True,
                        output=stdout,
                        error=stderr if stderr else None,
                        exit_code=exit_code
                    )
                else:
                    return SkillInvocationResult(
                        success=False,
                        output=stdout,
                        error=stderr or f"Skill exited with code {exit_code}",
                        exit_code=exit_code
                    )
            
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                
                return SkillInvocationResult(
                    success=False,
                    output=stdout,
                    error=f"Skill execution timed out after {timeout}s",
                    exit_code=1
                )
        
        except Exception as e:
            return SkillInvocationResult(
                success=False,
                output="",
                error=f"Failed to execute skill: {str(e)}",
                exit_code=1
            )
    
    def _validate_skill_output(
        self,
        skill_name: str,
        output: str,
        config: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate skill output against schema if configured."""
        # Check if validation schema is configured
        validation_config = config.get('validation', {})
        
        if not validation_config:
            return True, None
        
        # Check for required patterns
        required_patterns = validation_config.get('required_patterns', [])
        for pattern in required_patterns:
            import re
            if not re.search(pattern, output):
                return False, f"Output missing required pattern: {pattern}"
        
        # Check for forbidden patterns
        forbidden_patterns = validation_config.get('forbidden_patterns', [])
        for pattern in forbidden_patterns:
            import re
            if re.search(pattern, output):
                return False, f"Output contains forbidden pattern: {pattern}"
        
        # Check for minimum length
        min_length = validation_config.get('min_length', 0)
        if len(output) < min_length:
            return False, f"Output too short: {len(output)} < {min_length}"
        
        # Check for maximum length
        max_length = validation_config.get('max_length', float('inf'))
        if len(output) > max_length:
            return False, f"Output too long: {len(output)} > {max_length}"
        
        return True, None
    
    def invoke_skill_parallel(
        self,
        invocations: List[Tuple[str, str, Dict[str, Any]]],
        timeout: Optional[int] = None
    ) -> List[SkillInvocationResult]:
        """Invoke multiple skills in parallel.
        
        Args:
            invocations: List of (skill_name, prompt, context) tuples
            timeout: Execution timeout for each skill
            
        Returns:
            List of SkillInvocationResult
        """
        # For now, execute sequentially (parallel execution would require threading/asyncio)
        results = []
        
        for skill_name, prompt, context in invocations:
            result = self.invoke_skill(
                skill_name,
                prompt,
                context,
                timeout=timeout
            )
            results.append(result)
        
        return results
    
    def get_execution_history(self, limit: int = 100) -> List[SkillInvocationResult]:
        """Get recent skill execution history.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of SkillInvocationResult
        """
        return self.execution_history[-limit:]
    
    def get_skill_success_rate(self, skill_name: str) -> float:
        """Calculate success rate for a specific skill.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            Success rate as a percentage (0-100)
        """
        skill_executions = [
            r for r in self.execution_history
            if r.metadata.get('skill_name') == skill_name
        ]
        
        if not skill_executions:
            return 0.0
        
        successful = sum(1 for r in skill_executions if r.success)
        return (successful / len(skill_executions)) * 100


def create_skill_invoker(
    skills_dir: Path,
    repo_root: Path,
    dry_run: bool = False,
    default_timeout: int = Timeouts.SKILL_INVOCATION.value
) -> SkillInvoker:
    """Create a skill invoker instance."""
    return SkillInvoker(
        skills_dir=skills_dir,
        repo_root=repo_root,
        dry_run=dry_run,
        default_timeout=default_timeout
    )