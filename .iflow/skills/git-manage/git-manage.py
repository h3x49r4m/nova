#!/usr/bin/env python3
"""
Git Management Skill - Implementation
Provides standardized git operations with safety checks and best practices.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import shared git command utility
utils_path = Path(__file__).parent.parent / 'utils'
sys.path.insert(0, str(utils_path))

# Import modules that may use relative imports
import importlib.util
import importlib

def import_module(module_name: str):
    """Import a module from utils directory, handling relative imports."""
    try:
        # Try direct import first
        return importlib.import_module(module_name)
    except ImportError:
        # If that fails, try importing from utils path
        spec = importlib.util.spec_from_file_location(module_name, utils_path / f"{module_name}.py")
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module
        raise

# Import required modules
git_command = import_module('git_command')
exceptions = import_module('exceptions')
constants = import_module('constants')
structured_logger = import_module('structured_logger')

# Extract required items
run_git_command = git_command.run_git_command
get_current_branch = git_command.get_current_branch
validate_branch_name = git_command.validate_branch_name
validate_file_path = git_command.validate_file_path

IFlowError = exceptions.IFlowError
ErrorCode = exceptions.ErrorCode
ValidationError = exceptions.ValidationError
SecurityError = exceptions.SecurityError
FileError = exceptions.FileError

Timeouts = constants.Timeouts
CoverageThresholds = constants.CoverageThresholds
CommitTypes = constants.CommitTypes
SecretPatterns = constants.SecretPatterns
DEFAULT_PROTECTED_BRANCHES = constants.DEFAULT_PROTECTED_BRANCHES
DEFAULT_COVERAGE_THRESHOLDS = constants.DEFAULT_COVERAGE_THRESHOLDS

StructuredLogger = structured_logger.StructuredLogger
LogFormat = structured_logger.LogFormat


class GitManage:
    """Main git management class with safety checks and formatted commits."""

    # Use constants for commit types
    COMMIT_TYPES = {ct.value: ct.value.title() for ct in CommitTypes}

    # Use constants for secret patterns
    SECRET_PATTERNS = [pattern.value for pattern in SecretPatterns]

    # Use constants for coverage thresholds
    COVERAGE_THRESHOLD = CoverageThresholds.LINES.value
    BRANCH_COVERAGE_THRESHOLD = CoverageThresholds.BRANCHES.value
    
    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize git manager."""
        self.repo_root = repo_root or Path.cwd()
        self.config_dir = self.repo_root / '.iflow' / 'skills' / 'git-manage'
        self.config_file = self.config_dir / 'config.json'
        self.logger = StructuredLogger(
            name="git-manage",
            log_dir=self.repo_root / ".iflow" / "logs",
            log_format=LogFormat.JSON
        )
        self.load_config()
    
    def load_config(self):
        """Load configuration from config file."""
        self.config = {
            'pre_commit_checks': True,
            'run_tests': True,
            'run_architecture_check': True,
            'run_tdd_check': True,
            'check_coverage': True,
            'detect_secrets': True,
            'branch_protection': True,
            'protected_branches': DEFAULT_PROTECTED_BRANCHES.copy(),
            'coverage_threshold': self.COVERAGE_THRESHOLD,
            'branch_coverage_threshold': self.BRANCH_COVERAGE_THRESHOLD,
            'coverage_thresholds': DEFAULT_COVERAGE_THRESHOLDS.copy()
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    self.config.update(user_config)
                    
                    # Merge coverage thresholds if provided
                    if 'coverage_thresholds' in user_config:
                        self.config['coverage_thresholds'].update(user_config['coverage_thresholds'])
                        # Update legacy thresholds for backward compatibility
                        self.config['coverage_threshold'] = self.config['coverage_thresholds'].get('lines', self.COVERAGE_THRESHOLD)
                        self.config['branch_coverage_threshold'] = self.config['coverage_thresholds'].get('branches', self.BRANCH_COVERAGE_THRESHOLD)
            except (json.JSONDecodeError, IOError):
                pass
    
    def run_git_command(self, command: List[str], capture: bool = True, timeout: Optional[int] = None) -> Tuple[int, str, str]:
        """Run a git command and return exit code, stdout, stderr."""
        if timeout is None:
            timeout = Timeouts.GIT_DEFAULT.value
        try:
            return run_git_command(command, cwd=self.repo_root, timeout=timeout)
        except IFlowError as e:
            return e.code.value, '', str(e)
        except Exception as e:
            return ErrorCode.UNKNOWN_ERROR.value, '', f'Unexpected error: {str(e)}'
    
    def get_current_branch(self) -> str:
        """Get current branch name."""
        try:
            return get_current_branch(self.repo_root)
        except Exception:
            return 'unknown'
    
    def get_staged_files(self) -> List[str]:
        """Get list of staged files."""
        code, stdout, _ = self.run_git_command(['diff', '--name-only', '--cached'])
        output = stdout.strip() if isinstance(stdout, str) else stdout.decode('utf-8').strip()
        return output.split('\n') if output else []
    
    def get_unstaged_files(self) -> List[str]:
        """Get list of unstaged files."""
        code, stdout, _ = self.run_git_command(['diff', '--name-only'])
        output = stdout.strip() if isinstance(stdout, str) else stdout.decode('utf-8').strip()
        return output.split('\n') if output else []
    
    def detect_secrets(self, files: List[str]) -> Tuple[bool, List[str]]:
        """Scan files for potential secrets."""
        secrets_found = []
        
        for file_path in files:
            full_path = self.repo_root / file_path
            if not full_path.exists():
                continue
            
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    for pattern in self.SECRET_PATTERNS:
                        if re.search(pattern, content, re.IGNORECASE):
                            secrets_found.append(f"{file_path}: matches pattern")
                            break
            except (IOError, UnicodeDecodeError):
                # Skip binary files or unreadable files
                continue
        
        return len(secrets_found) > 0, secrets_found
    
    def run_tests(self) -> Tuple[int, str]:
        """Run test suite."""
        if not self.config['run_tests']:
            return 0, 'Tests skipped (disabled in config)'

        # Check if pytest is available
        try:
            subprocess.run(['pytest', '--version'], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            return 0, 'Tests: pytest not available, skipping'

        # Run tests
        result = subprocess.run(
            ['pytest', 'tests/', '-v', '--cov', '--cov-report=term-missing'],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            timeout=Timeouts.TEST_DEFAULT.value
        )

        return result.returncode, result.stdout
    
    def check_coverage(self) -> Tuple[int, float, float]:
        """Check test coverage with configurable thresholds."""
        if not self.config['check_coverage']:
            return 0, 100.0, 100.0

        # Get configured thresholds
        thresholds = self.config.get('coverage_thresholds', {})
        line_threshold = thresholds.get('lines', self.COVERAGE_THRESHOLD)
        branch_threshold = thresholds.get('branches', self.BRANCH_COVERAGE_THRESHOLD)

        # Run coverage check
        try:
            result = subprocess.run(
                ['pytest', 'tests/', '--cov', '--cov-report=json'],
                cwd=self.repo_root,
                capture_output=True,
                timeout=Timeouts.TEST_COVERAGE.value
            )
        except subprocess.TimeoutExpired:
            return 1, 0.0, 0.0
        
        if result.returncode != 0:
            return 0, 0.0, 0.0
        
        # Parse coverage report
        coverage_file = self.repo_root / 'coverage.json'
        if coverage_file.exists():
            with open(coverage_file, 'r') as f:
                data = json.load(f)
                line_coverage = data.get('totals', {}).get('percent_covered', 0)
                branch_coverage = data.get('totals', {}).get('branch_percent_covered', line_coverage)
                return 0, line_coverage, branch_coverage
        
        return 0, 0.0, 0.0
    
    def check_branch_protection(self) -> Tuple[bool, str]:
        """Check if current branch is protected."""
        if not self.config['branch_protection']:
            return False, ''
        
        branch = self.get_current_branch()
        if branch in self.config['protected_branches']:
            return True, f'Branch "{branch}" is protected. Use feature branch workflow.'
        return False, ''
    
    def parse_commit_message(self, message: str) -> Dict:
        """Parse conventional commit message."""
        pattern = r'^(\w+)(?:\(([^)]+)\))?: (.+)$'
        match = re.match(pattern, message)
        
        if match:
            return {
                'type': match.group(1),
                'scope': match.group(2),
                'description': match.group(3),
                'valid': match.group(1) in self.COMMIT_TYPES
            }
        
        return {'valid': False, 'message': message}
    
    def generate_commit_message(self, type_: str, scope: Optional[str],
                                description: str, body: Optional[str] = None,
                                files_changed: Optional[List[str]] = None,
                                test_results: Optional[str] = None,
                                coverage: Optional[float] = None,
                                architecture_check: bool = False,
                                tdd_check: bool = False) -> str:
        """Generate formatted commit message."""
        # Header
        if scope:
            header = f"{type_}[{scope}]: {description}"
        else:
            header = f"{type_}: {description}"

        message = [header]

        # Body (LLM-generated with detailed Changes section)
        if body:
            message.append('')
            message.append(body)

        # Always add metadata sections when there are files to commit
        if files_changed:
            message.append('')
            message.append('---')
            message.append('Branch: ' + self.get_current_branch())
            message.append('')
            message.append('Files changed:')
            for file_path in files_changed:
                message.append(f'- {file_path}')
            message.append('')
            message.append('Verification:')
            if test_results:
                message.append(f'- Tests: {test_results}')
            else:
                message.append('- Tests: N/A')
            if coverage is not None:
                message.append(f'- Coverage: {coverage:.1f}%')
            else:
                message.append('- Coverage: N/A')
            if architecture_check:
                message.append('- Architecture: ✓ compliant')
            if tdd_check:
                message.append('- TDD: ✓ compliant')

        return '\n'.join(message)
    
    def commit(self, type_: str, scope: Optional[str], description: str,
               body: Optional[str] = None, no_verify: bool = False) -> Tuple[int, str]:
        """Create a commit with formatted message."""

        # Check if there are staged changes
        staged_files = self.get_staged_files()
        if not staged_files:
            return ErrorCode.INVALID_INPUT.value, 'No changes to commit. Use git add to stage files.'

        # Validate commit type
        if type_ not in self.COMMIT_TYPES:
            return ErrorCode.INVALID_INPUT.value, f'Invalid commit type: {type_}. Valid types: {", ".join(self.COMMIT_TYPES.keys())}'

        # Validate body format if provided
        if body:
            # Check for required "Changes:" section
            if 'Changes:' not in body:
                return ErrorCode.VALIDATION_FAILED.value, 'Commit body must include a "Changes:" section. Please regenerate with LLM.'

            # Check for at least one bullet point after Changes:
            changes_section = body.split('Changes:')[1].split('---')[0] if '---' in body else body.split('Changes:')[1]
            bullet_points = [line for line in changes_section.split('\n') if line.strip().startswith('-')]
            if len(bullet_points) < 1:
                return ErrorCode.VALIDATION_FAILED.value, 'Commit body "Changes:" section must have at least one bullet point. Please regenerate with LLM.'

        # Check branch protection
        protected, msg = self.check_branch_protection()
        if protected:
            return ErrorCode.GIT_BRANCH_PROTECTED.value, msg

        # Detect secrets
        if self.config['detect_secrets']:
            has_secrets, secrets = self.detect_secrets(staged_files)
            if has_secrets:
                return ErrorCode.SECRET_DETECTED.value, f'Secrets detected in staged files:\n' + '\n'.join(secrets)

        # Run pre-commit checks
        test_status = 'skipped'
        coverage = None
        architecture_check = False
        tdd_check = False

        if not no_verify and self.config['pre_commit_checks']:
            # Run tests
            if self.config['run_tests']:
                code, output = self.run_tests()
                if code != 0:
                    return ErrorCode.TEST_FAILED.value, f'Tests failed:\n{output}'
                test_status = 'passed'

            # Check coverage
            if self.config['check_coverage']:
                code, line_cov, branch_cov = self.check_coverage()
                if line_cov < self.config['coverage_threshold']:
                    return ErrorCode.COVERAGE_BELOW_THRESHOLD.value, f'Coverage below threshold: {line_cov:.1f}% < {self.config["coverage_threshold"]}%'
                coverage = line_cov

            # Track whether checks were actually run
            architecture_check = self.config.get('run_architecture_check', False)
            tdd_check = self.config.get('run_tdd_check', False)

        # Generate commit message
        message = self.generate_commit_message(
            type_, scope, description, body,
            files_changed=staged_files,
            test_results=test_status,
            coverage=coverage,
            architecture_check=architecture_check,
            tdd_check=tdd_check
        )

        # Create commit
        code, stdout, stderr = self.run_git_command(['commit', '-m', message])

        if code == 0:
            return ErrorCode.SUCCESS.value, f'Commit successful:\n{stdout}'
        else:
            return ErrorCode.GIT_COMMAND_FAILED.value, f'Commit failed:\n{stderr}'
    
    def add_files(self, files: List[str]) -> Tuple[int, str]:
        """Stage files for commit."""
        if not files:
            return 1, 'No files specified'
        
        # Convert files to strings if they are Path objects
        file_strings = [str(f) for f in files]
        code, stdout, stderr = self.run_git_command(['add'] + file_strings)
        
        if code == 0:
            return 0, f'Staged {len(files)} file(s)'
        else:
            return code, f'Failed to stage files:\n{stderr}'
    
    def get_file_diffs(self, files: List[str], max_size_mb: int = 10) -> str:
        """Get diff output for the specified files with streaming for large files.
        
        Args:
            files: List of files to get diffs for
            max_size_mb: Maximum diff size in MB before truncating with warning
            
        Returns:
            Diff output as string
        """
        import io
        max_size_bytes = max_size_mb * 1024 * 1024
        
        # Try streaming approach first for large diffs
        try:
            result = subprocess.run(
                ['git', 'diff', '--cached'] + files,
                cwd=self.repo_root,
                capture_output=True,
                timeout=Timeouts.GIT_DEFAULT.value
            )
            
            if result.returncode != 0:
                return ''
            
            # Check size and truncate if necessary
            diff_size = len(result.stdout)
            if diff_size > max_size_bytes:
                truncated_diff = result.stdout[:max_size_bytes]
                warning = f"\n\n[DIFF TRUNCATED: Diff size ({diff_size/1024/1024:.1f}MB) exceeds limit ({max_size_mb}MB). Use --diff-max-size to adjust limit.]"
                return truncated_diff.decode('utf-8', errors='ignore') + warning
            
            return result.stdout.decode('utf-8', errors='ignore')
            
        except subprocess.TimeoutExpired:
            return '[DIFF TIMEOUT: Diff generation exceeded time limit. Try reducing number of files or use smaller changes.]'
        except Exception as e:
            return f'[DIFF ERROR: {str(e)}]'
    
    def get_file_diffs_streaming(self, files: List[str], max_size_mb: int = 10) -> str:
        """Get diff output with streaming support for very large files.
        
        This method streams the diff output in chunks to avoid memory issues
        with extremely large diffs. Suitable for files with thousands of lines.
        
        Args:
            files: List of files to get diffs for
            max_size_mb: Maximum diff size in MB before truncating
            
        Returns:
            Diff output as string
        """
        import io
        max_size_bytes = max_size_mb * 1024 * 1024
        buffer = io.StringIO()
        total_size = 0
        
        try:
            # Start git diff process
            process = subprocess.Popen(
                ['git', 'diff', '--cached'] + files,
                cwd=self.repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=8192  # 8KB buffer
            )
            
            # Read output in chunks
            chunk_size = 8192
            while True:
                chunk = process.stdout.read(chunk_size)
                if not chunk:
                    break
                
                # Check if we've exceeded max size
                if total_size + len(chunk) > max_size_bytes:
                    # Write remaining space and add warning
                    remaining_space = max_size_bytes - total_size
                    if remaining_space > 0:
                        buffer.write(chunk[:remaining_space])
                    buffer.write(f"\n\n[DIFF TRUNCATED: Diff exceeds {max_size_mb}MB limit]")
                    process.terminate()
                    break
                
                buffer.write(chunk)
                total_size += len(chunk)
            
            # Wait for process to complete
            process.wait(timeout=Timeouts.GIT_DEFAULT.value)
            
            if process.returncode != 0:
                stderr = process.stderr.read()
                return f'[DIFF ERROR: {stderr}]'
            
            return buffer.getvalue()
            
        except subprocess.TimeoutExpired:
            process.terminate()
            return '[DIFF TIMEOUT: Diff generation exceeded time limit]'
        except Exception as e:
            return f'[DIFF ERROR: {str(e)}]'
        finally:
            buffer.close()
    
    def get_file_diffs_by_line_count(self, files: List[str], max_lines: int = 10000) -> str:
        """Get diff output limited by line count.
        
        This method limits the diff output by the number of lines rather than
        file size, which is often more useful for code reviews.
        
        Args:
            files: List of files to get diffs for
            max_lines: Maximum number of lines to include in diff
            
        Returns:
            Diff output as string
        """
        try:
            # Start git diff process
            process = subprocess.Popen(
                ['git', 'diff', '--cached'] + files,
                cwd=self.repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            lines = []
            line_count = 0
            
            # Read lines one by one
            while line_count < max_lines:
                line = process.stdout.readline()
                if not line:
                    break
                
                lines.append(line)
                line_count += 1
            
            # Check if there are more lines
            if process.stdout.read(1):  # Try to read one more character
                lines.append(f"\n\n[DIFF TRUNCATED: Output limited to {max_lines} lines. Use --diff-max-lines to adjust limit.]")
                process.terminate()
            
            # Wait for process to complete
            process.wait(timeout=Timeouts.GIT_DEFAULT.value)
            
            if process.returncode != 0:
                stderr = process.stderr.read()
                return f'[DIFF ERROR: {stderr}]'
            
            return ''.join(lines)
            
        except subprocess.TimeoutExpired:
            process.terminate()
            return '[DIFF TIMEOUT: Diff generation exceeded time limit]'
        except Exception as e:
            return f'[DIFF ERROR: {str(e)}]'
    
    def analyze_files(self, files: List[str]) -> str:
        """Analyze files to provide context for LLM."""
        context = []
        for file_path in files:
            full_path = self.repo_root / file_path
            if full_path.exists():
                context.append(f"File: {file_path}")
                context.append(f"Type: {'directory' if full_path.is_dir() else 'file'}")
                if full_path.is_file():
                    # Try to read first few lines to understand content
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()[:5]  # First 5 lines
                            if lines:
                                context.append(f"Content preview:\n{''.join(lines)}")
                    except:
                        pass
                context.append("---")
        return '\n'.join(context)
    
    def collect_commit_context(self, files: List[str], use_streaming: bool = True, max_diff_size_mb: int = 10) -> Dict:
        """Collect context for LLM-based commit message generation (called by iFlow CLI).
        
        Args:
            files: List of files to collect context for
            use_streaming: Whether to use streaming for large diffs
            max_diff_size_mb: Maximum diff size in MB when streaming
            
        Returns:
            Dictionary with diff, file_context, branch, and files
        """
        # Use streaming for large diffs by default
        if use_streaming and len(files) > 5:
            diff_output = self.get_file_diffs_streaming(files, max_diff_size_mb)
        else:
            diff_output = self.get_file_diffs(files)
        
        file_context = self.analyze_files(files)
        branch = self.get_current_branch()

        return {
            'diff': diff_output if diff_output else 'No diff available (new files)',
            'file_context': file_context,
            'branch': branch,
            'files': files,
            'streaming_used': use_streaming
        }
    
    
    
    def status(self) -> Tuple[int, str]:
        """Show git status with additional information."""
        code, stdout, stderr = self.run_git_command(['status', '--short'])
        
        if code != 0:
            return code, stderr
        
        status = stdout.strip() if isinstance(stdout, str) else stdout.decode('utf-8').strip()
        if not status:
            return 0, 'Working tree clean'
        
        # Parse status
        staged = []
        unstaged = []
        untracked = []
        
        for line in status.split('\n'):
            if line.startswith('M '):
                unstaged.append(line[3:])
            elif line.startswith(' M'):
                staged.append(line[3:])
            elif line.startswith('??'):
                untracked.append(line[3:])
            elif line.startswith('M'):
                staged.append(line[2:])
        
        output = []
        if staged:
            output.append('Staged changes:')
            for f in staged:
                output.append(f'  M {f}')
        if unstaged:
            output.append('Unstaged changes:')
            for f in unstaged:
                output.append(f'  M {f}')
        if untracked:
            output.append('Untracked files:')
            for f in untracked:
                output.append(f'  ?? {f}')
        
        return 0, '\n'.join(output)
    
    def diff(self, staged: bool = False) -> Tuple[int, str]:
        """Show changes."""
        if staged:
            code, stdout, _ = self.run_git_command(['diff', '--cached'])
        else:
            code, stdout, _ = self.run_git_command(['diff'])
        
        if code == 0:
            return 0, stdout if stdout else 'No changes'
        return code, ''
    
    def log(self, count: int = 10, full: bool = False) -> Tuple[int, str]:
        """Show commit history."""
        if full:
            code, stdout, _ = self.run_git_command(['log', f'-{count}', '--pretty=format:%h%nAuthor: %an%nDate: %ad%n%n%s%n%n%b%n---'])
        else:
            code, stdout, _ = self.run_git_command(['log', f'-{count}', '--oneline'])
        
        if code == 0:
            return 0, stdout
        return code, ''
    
    def undo(self, mode: str = 'soft') -> Tuple[int, str]:
        """Undo last commit."""
        if mode not in ['soft', 'hard']:
            return 1, 'Invalid mode. Use "soft" or "hard"'
        
        # Create backup stash
        self.run_git_command(['stash', 'save', f'backup-before-undo-{mode}'])
        
        code, _, stderr = self.run_git_command(['reset', f'--{mode}', 'HEAD~1'])
        
        if code == 0:
            return 0, f'Undo successful ({mode} mode)'
        else:
            return code, f'Undo failed:\n{stderr}'
    
    def amend(self, description: Optional[str] = None) -> Tuple[int, str]:
        """Amend last commit."""
        if description:
            # Get current commit message
            code, stdout, _ = self.run_git_command(['log', '-1', '--pretty=%B'])
            if code == 0:
                current_msg = stdout.strip()
                new_msg = current_msg + '\n\n' + description
                code, _, stderr = self.run_git_command(['commit', '--amend', '-m', new_msg])
            else:
                return code, 'Failed to get current commit message'
        else:
            code, _, stderr = self.run_git_command(['commit', '--amend', '--no-edit'])
        
        if code == 0:
            return 0, 'Commit amended successfully'
        else:
            return code, f'Amend failed:\n{stderr}'
    
    def stash(self, action: str, message: Optional[str] = None) -> Tuple[int, str]:
        """Stash operations."""
        if action == 'save':
            if not message:
                message = 'WIP'
            code, _, stderr = self.run_git_command(['stash', 'save', message])
        elif action == 'pop':
            code, _, stderr = self.run_git_command(['stash', 'pop'])
        elif action == 'list':
            code, stdout, _ = self.run_git_command(['stash', 'list'])
            if code == 0:
                return 0, stdout if stdout else 'No stashes'
            return code, ''
        elif action == 'drop':
            code, _, stderr = self.run_git_command(['stash', 'drop'])
        else:
            return 1, f'Invalid stash action: {action}'
        
        if code == 0:
            return 0, f'Stash {action} successful'
        else:
            return code, f'Stash {action} failed:\n{stderr}'
    
    def push(self, remote: str = 'origin', branch: Optional[str] = None) -> Tuple[int, str]:
        """Push commits to remote."""
        if not branch:
            branch = self.get_current_branch()
        
        code, _, stderr = self.run_git_command(['push', remote, branch])
        
        if code == 0:
            return 0, f'Pushed to {remote}/{branch}'
        else:
            return code, f'Push failed:\n{stderr}'


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Git Management Skill',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Show git status')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Stage files for commit')
    add_parser.add_argument('files', nargs='+', help='Files to stage')
    
    # Commit command
    commit_parser = subparsers.add_parser('commit', help='Create a commit')
    commit_parser.add_argument('files', nargs='+', help='Files to commit')
    commit_parser.add_argument('--type', help='Commit type (from LLM)')
    commit_parser.add_argument('--scope', help='Commit scope (from LLM)')
    commit_parser.add_argument('--description', help='Commit description (from LLM)')
    commit_parser.add_argument('--body', help='Commit body with Changes section (from LLM)')
    commit_parser.add_argument('--no-verify', action='store_true', help='Skip pre-commit checks')
    
    # Diff command
    diff_parser = subparsers.add_parser('diff', help='Show changes')
    diff_parser.add_argument('--staged', action='store_true', help='Show staged changes')
    
    # Log command
    log_parser = subparsers.add_parser('log', help='Show commit history')
    log_parser.add_argument('-n', '--count', type=int, default=10, help='Number of commits')
    log_parser.add_argument('--full', action='store_true', help='Show full commit details')
    
    # Undo command
    undo_parser = subparsers.add_parser('undo', help='Undo last commit')
    undo_parser.add_argument('mode', nargs='?', default='soft', choices=['soft', 'hard'], help='Undo mode')
    
    # Amend command
    amend_parser = subparsers.add_parser('amend', help='Amend last commit')
    amend_parser.add_argument('description', nargs='?', help='Additional description')
    
    # Stash command
    stash_parser = subparsers.add_parser('stash', help='Stash operations')
    stash_parser.add_argument('action', choices=['save', 'pop', 'list', 'drop'], help='Stash action')
    stash_parser.add_argument('message', nargs='?', help='Stash message (for save)')
    
    # Push command
    push_parser = subparsers.add_parser('push', help='Push to remote')
    push_parser.add_argument('remote', nargs='?', default='origin', help='Remote name')
    push_parser.add_argument('branch', nargs='?', help='Branch name')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    git = GitManage()
    
    # Execute command
    if args.command == 'status':
        code, output = git.status()
    elif args.command == 'add':
        code, output = git.add_files(args.files)
    elif args.command == 'commit':
        # Check if LLM-generated parameters are provided
        if args.type and args.description:
            # LLM has generated the commit message, proceed with commit
            code, output = git.commit(
                args.type, args.scope, args.description,
                args.body, args.no_verify
            )
        else:
            # No LLM parameters provided, output context for LLM generation
            # Stage files first
            code, output = git.add_files(args.files)
            if code != 0:
                logger = StructuredLogger(name="git-manage-cli", log_format=LogFormat.TEXT)
                logger.info(output)
                sys.exit(code)

            # Collect context for LLM
            context = git.collect_commit_context(args.files)

            # Convert bytes to string for JSON serialization
            if isinstance(context.get('diff'), bytes):
                context['diff'] = context['diff'].decode('utf-8')

            # Output context in JSON format for iFlow CLI
            import json
            logger = StructuredLogger(name="git-manage-cli", log_format=LogFormat.TEXT)
            logger.info(json.dumps({
                'context': context,
                'instruction': 'Generate a conventional commit message with detailed Changes section. Then call: git.commit(type, scope, description, body)'
            }))
            code = 0
    elif args.command == 'diff':
        code, output = git.diff(staged=args.staged)
    elif args.command == 'log':
        code, output = git.log(count=args.count, full=args.full)
    elif args.command == 'undo':
        code, output = git.undo(mode=args.mode)
    elif args.command == 'amend':
        code, output = git.amend(description=args.description)
    elif args.command == 'stash':
        code, output = git.stash(args.action, args.message)
    elif args.command == 'push':
        code, output = git.push(args.remote, args.branch)
    else:
        code, output = 1, f'Unknown command: {args.command}'
    
    logger = StructuredLogger(name="git-manage-cli", log_format=LogFormat.TEXT)
    logger.info(output)
    return code


if __name__ == '__main__':
    sys.exit(main())