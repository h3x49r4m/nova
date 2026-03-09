#!/usr/bin/env python3
"""
Test suite for utility modules (git_command.py, schema_validator.py, file_lock.py)
Tests shared utilities used across the skills system.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from threading import Thread
import time

# Import utility classes
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.git_command import (
    run_git_command,
    validate_git_repo,
    get_current_branch,
    get_repo_root,
    validate_branch_name,
    validate_file_path,
    check_for_secrets,
    GitError,
    ErrorCode,
    ErrorCategory
)
from utils.schema_validator import (
    SchemaValidator
)
from utils.file_lock import FileLock, FileLockError
from utils.constants import (
    Timeouts,
    CommitTypes,
    SecretPatterns,
    ValidationPatterns
)
from utils.input_sanitizer import InputSanitizer
from utils.exceptions import IFlowError, ValidationError


class TestGitCommand(unittest.TestCase):
    """Test git_command utilities."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_root = Path(self.temp_dir)

        # Initialize git repo
        import subprocess
        subprocess.run(['git', 'init'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'checkout', '-b', 'main'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'commit', '--allow-empty', '-m', 'Initial'], cwd=self.repo_root, capture_output=True)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_run_git_command_success(self):
        """Test running a successful git command."""
        returncode, stdout, stderr = run_git_command(['status'], cwd=self.repo_root)

        self.assertEqual(returncode, 0)
        self.assertIsInstance(stdout, str)

    def test_run_git_command_failure(self):
        """Test running a git command that fails."""
        with self.assertRaises(GitError) as context:
            run_git_command(['invalid-command'], cwd=self.repo_root)

        self.assertIn('unknown', str(context.exception).lower())

    @patch('subprocess.run')
    def test_run_git_command_timeout(self, mock_run):
        """Test git command timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(['git', 'test'], 10)

        with self.assertRaises(GitError) as context:
            run_git_command(['test'], cwd=self.repo_root, timeout=5)

        self.assertEqual(context.exception.code, ErrorCode.TIMEOUT)

    @patch('subprocess.run')
    def test_run_git_command_not_found(self, mock_run):
        """Test git command when git not found."""
        mock_run.side_effect = FileNotFoundError()

        with self.assertRaises(GitError) as context:
            run_git_command(['test'], cwd=self.repo_root)

        self.assertEqual(context.exception.code, ErrorCode.GIT_NOT_FOUND)

    def test_validate_git_repo_true(self):
        """Test validating a git repo (should be true)."""
        is_valid = validate_git_repo(self.repo_root)
        self.assertTrue(is_valid)

    def test_validate_git_repo_false(self):
        """Test validating a non-git directory."""
        non_repo_dir = self.temp_dir / 'non_repo'
        non_repo_dir.mkdir()
        is_valid = validate_git_repo(non_repo_dir)
        self.assertFalse(is_valid)

    def test_get_current_branch(self):
        """Test getting current branch."""
        branch = get_current_branch(self.repo_root)
        self.assertEqual(branch, 'main')

    def test_get_repo_root(self):
        """Test getting repository root."""
        root = get_repo_root(self.repo_root)
        self.assertEqual(root, self.repo_root)

    def test_get_repo_root_not_in_repo(self):
        """Test getting repo root when not in a repo."""
        non_repo_dir = self.temp_dir / 'non_repo'
        non_repo_dir.mkdir()
        root = get_repo_root(non_repo_dir)
        self.assertIsNone(root)

    def test_validate_branch_name_valid(self):
        """Test validating valid branch names."""
        test_cases = [
            'main',
            'feature/test',
            'bugfix/issue-123',
            'release/v1.0.0',
            'develop'
        ]

        for branch_name in test_cases:
            is_valid, error = validate_branch_name(branch_name)
            self.assertTrue(is_valid, f"Branch {branch_name} should be valid")
            self.assertIsNone(error)

    def test_validate_branch_name_invalid(self):
        """Test validating invalid branch names."""
        test_cases = [
            ('.invalid', 'cannot begin with a dot'),
            ('invalid.', 'cannot end with a dot'),
            ('invalid..name', 'cannot contain ..'),
            ('invalid @{', 'cannot contain @{'),
            ('invalid name', 'cannot contain space'),
            ('/invalid', 'cannot begin with slash'),
            ('invalid/', 'cannot end with slash'),
            ('invalid//name', 'cannot contain consecutive slashes'),
            ('invalid.lock', 'cannot end with .lock')
        ]

        for branch_name, expected_error in test_cases:
            is_valid, error = validate_branch_name(branch_name)
            self.assertFalse(is_valid, f"Branch {branch_name} should be invalid")
            self.assertIn(expected_error.lower(), error.lower())

    def test_validate_branch_name_empty(self):
        """Test validating empty branch name."""
        is_valid, error = validate_branch_name('')
        self.assertFalse(is_valid)
        self.assertIn('empty', error.lower())

    def test_validate_file_path_valid(self):
        """Test validating valid file paths."""
        test_cases = [
            'src/file.py',
            'tests/test_file.py',
            'docs/readme.md',
            'data/config.json'
        ]

        for file_path in test_cases:
            is_valid, error = validate_file_path(file_path, self.repo_root)
            self.assertTrue(is_valid, f"Path {file_path} should be valid")
            self.assertIsNone(error)

    def test_validate_file_path_invalid_traversal(self):
        """Test validating file path with traversal."""
        test_cases = [
            '../etc/passwd',
            '..\\windows\\system32',
            '../../secret.txt'
        ]

        for file_path in test_cases:
            is_valid, error = validate_file_path(file_path, self.repo_root)
            self.assertFalse(is_valid, f"Path {file_path} should be invalid")
            self.assertIn('traversal', error.lower())

    def test_validate_file_path_empty(self):
        """Test validating empty file path."""
        is_valid, error = validate_file_path('')
        self.assertFalse(is_valid)
        self.assertIn('empty', error.lower())

    def test_validate_file_path_absolute(self):
        """Test validating absolute path within repo."""
        abs_path = str(self.repo_root / 'test.txt')
        is_valid, error = validate_file_path(abs_path, self.repo_root)
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_file_path_absolute_outside_repo(self):
        """Test validating absolute path outside repo."""
        outside_path = '/tmp/test.txt'
        is_valid, error = validate_file_path(outside_path, self.repo_root)
        self.assertFalse(is_valid)
        self.assertIn('outside', error.lower())


class TestSecretDetection(unittest.TestCase):
    """Test secret detection functionality."""

    def test_check_for_secrets_api_key(self):
        """Test detecting API key secrets."""
        stdout = "API_KEY='test_fake_key_for_testing_only_12345'"
        stderr = ""

        self.assertTrue(check_for_secrets(stdout, stderr))

    def test_check_for_secrets_password(self):
        """Test detecting password secrets."""
        stdout = "password='MySecretPassword123'"
        stderr = ""
        
        self.assertTrue(check_for_secrets(stdout, stderr))

    def test_check_for_secrets_aws_keys(self):
        """Test detecting AWS access keys."""
        stdout = "aws_access_key_id=AKIAIOSFODNN7EXAMPLE"
        stderr = "aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        
        self.assertTrue(check_for_secrets(stdout, stderr))

    def test_check_for_secrets_jwt_token(self):
        """Test detecting JWT tokens."""
        stdout = "token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        stderr = ""
        
        self.assertTrue(check_for_secrets(stdout, stderr))

    def test_check_for_secrets_private_key(self):
        """Test detecting private keys."""
        stdout = "-----BEGIN RSA PRIVATE KEY-----"
        stderr = ""
        
        self.assertTrue(check_for_secrets(stdout, stderr))

    def test_check_for_secrets_github_token(self):
        """Test detecting GitHub tokens."""
        stdout = "github_token=ghp_1234567890abcdefghijklmnopqrstuvwxyz123456"
        stderr = ""
        
        self.assertTrue(check_for_secrets(stdout, stderr))

    def test_check_for_secrets_database_url(self):
        """Test detecting database URLs."""
        stdout = "database_url='postgresql://user:password123@localhost:5432/mydb'"
        stderr = ""
        
        self.assertTrue(check_for_secrets(stdout, stderr))

    def test_check_for_secrets_no_secrets(self):
        """Test output without secrets."""
        stdout = "This is normal output"
        stderr = "Some error message"
        
        self.assertFalse(check_for_secrets(stdout, stderr))

    def test_check_for_secrets_empty_output(self):
        """Test with empty output."""
        stdout = ""
        stderr = ""
        
        self.assertFalse(check_for_secrets(stdout, stderr))

    def test_check_for_secrets_case_insensitive(self):
        """Test that secret detection is case insensitive."""
        stdout = "API_KEY='secret'"
        stderr = "Password='test'"
        
        self.assertTrue(check_for_secrets(stdout, stderr))

    def test_check_for_secrets_multiple_patterns(self):
        """Test detecting multiple secret types."""
        stdout = "api_key='abc' and password='def'"
        stderr = ""
        
        self.assertTrue(check_for_secrets(stdout, stderr))

    def test_check_for_secrets_in_stderr(self):
        """Test detecting secrets in stderr."""
        stdout = ""
        stderr = "ERROR: secret token detected: abc123def456"
        
        self.assertTrue(check_for_secrets(stdout, stderr))


class TestSchemaValidator(unittest.TestCase):
    """Test schema validator."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.schema_dir = Path(self.temp_dir)
        self.schema_dir.mkdir()

        # Create test schema
        self.test_schema = {
            "version": "1.0.0",
            "required": ["name", "value"],
            "fields": {
                "name": {"type": "string"},
                "value": {"type": "integer", "minimum": 0, "maximum": 100},
                "description": {"type": "string"}
            }
        }

        schema_file = self.schema_dir / 'test-schema.json'
        schema_file.write_text(json.dumps(self.test_schema))

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_schema_validator_initialization(self):
        """Test SchemaValidator initialization."""
        validator = SchemaValidator(self.schema_dir)
        self.assertIsNotNone(validator)
        self.assertEqual(validator.schema_dir, self.schema_dir)

    def test_load_schema(self):
        """Test loading a schema."""
        validator = SchemaValidator(self.schema_dir)
        schema = validator.load_schema('test-schema')

        self.assertIsNotNone(schema)
        self.assertEqual(schema['version'], '1.0.0')

    def test_load_schema_not_found(self):
        """Test loading a non-existent schema."""
        validator = SchemaValidator(self.schema_dir)
        schema = validator.load_schema('non-existent')

        self.assertIsNone(schema)

    def test_validate_valid_data(self):
        """Test validating data against schema."""
        validator = SchemaValidator(self.schema_dir)
        data = {
            "name": "test",
            "value": 50,
            "description": "test data"
        }

        is_valid, errors = validator.validate(data, 'test-schema')

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_missing_required_field(self):
        """Test validation fails when required field missing."""
        validator = SchemaValidator(self.schema_dir)
        data = {
            "name": "test"
            # Missing 'value' field
        }

        is_valid, errors = validator.validate(data, 'test-schema')

        self.assertFalse(is_valid)
        self.assertTrue(any('value' in err for err in errors))

    def test_validate_wrong_type(self):
        """Test validation fails when field has wrong type."""
        validator = SchemaValidator(self.schema_dir)
        data = {
            "name": "test",
            "value": "not a number",  # Should be integer
            "description": "test"
        }

        is_valid, errors = validator.validate(data, 'test-schema')

        self.assertFalse(is_valid)
        self.assertTrue(any('integer' in err.lower() for err in errors))

    def test_validate_range_violation(self):
        """Test validation fails when value out of range."""
        validator = SchemaValidator(self.schema_dir)
        data = {
            "name": "test",
            "value": 150,  # Exceeds maximum of 100
            "description": "test"
        }

        is_valid, errors = validator.validate(data, 'test-schema')

        self.assertFalse(is_valid)
        self.assertTrue(any('greater' in err.lower() for err in errors))

    def test_validate_nested_object(self):
        """Test validating nested object."""
        schema_file = self.schema_dir / 'nested-schema.json'
        schema = {
            "version": "1.0.0",
            "required": ["name", "config"],
            "nested": {
                "config": {
                    "required": ["enabled"],
                    "fields": {"enabled": {"type": "boolean"}}
                }
            }
        }
        schema_file.write_text(json.dumps(schema))

        validator = SchemaValidator(self.schema_dir)
        data = {
            "name": "test",
            "config": {
                "enabled": True
            }
        }

        is_valid, errors = validator.validate(data, 'nested-schema')

        self.assertTrue(is_valid)

    def test_validate_array_field(self):
        """Test validating array field."""
        schema_file = self.schema_dir / 'array-schema.json'
        schema = {
            "version": "1.0.0",
            "fields": {
                "items": {"type": "array"}
            }
        }
        schema_file.write_text(json.dumps(schema))

        validator = SchemaValidator(self.schema_dir)
        data = {"items": [1, 2, 3]}

        is_valid, errors = validator.validate(data, 'array-schema')

        self.assertTrue(is_valid)


class TestFileLock(unittest.TestCase):
    """Test file lock utility."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / 'test.lock'

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_acquire_lock(self):
        """Test acquiring a file lock."""
        lock = FileLock(self.test_file, timeout=1)

        with lock:
            self.assertTrue(self.test_file.exists())

        # Lock file should be cleaned up
        self.assertFalse(self.test_file.exists())

    def test_acquire_lock_timeout(self):
        """Test lock acquisition timeout."""
        lock1 = FileLock(self.test_file, timeout=1)
        lock2 = FileLock(self.test_file, timeout=1)

        # Acquire first lock
        lock1.acquire()

        # Try to acquire second lock (should timeout)
        with self.assertRaises(FileLockError) as context:
            lock2.acquire()

        self.assertIn('timeout', str(context.exception).lower())

        # Release first lock
        lock1.release()

    def test_release_lock(self):
        """Test releasing a file lock."""
        lock = FileLock(self.test_file, timeout=1)
        lock.acquire()

        self.assertTrue(self.test_file.exists())

        lock.release()

        self.assertFalse(self.test_file.exists())

    def test_context_manager(self):
        """Test using lock as context manager."""
        with FileLock(self.test_file, timeout=1):
            self.assertTrue(self.test_file.exists())

        self.assertFalse(self.test_file.exists())

    def test_concurrent_access(self):
        """Test concurrent access to lock."""
        lock = FileLock(self.test_file, timeout=2)
        results = []

        def thread_func(thread_id):
            try:
                with lock:
                    results.append(f"Thread {thread_id} acquired lock")
                    time.sleep(0.1)
                    results.append(f"Thread {thread_id} released lock")
            except FileLockError as e:
                results.append(f"Thread {thread_id} failed: {e}")

        # Create multiple threads
        threads = [Thread(target=thread_func, args=(i,)) for i in range(3)]

        # Start threads
        for thread in threads:
            thread.start()

        # Wait for threads
        for thread in threads:
            thread.join()

        # All threads should have completed successfully
        self.assertEqual(len(results), 6)
        self.assertTrue(all('failed' not in r for r in results))


class TestConstants(unittest.TestCase):
    """Test constants module."""

    def test_timeouts_enum(self):
        """Test Timeouts enum values."""
        self.assertEqual(Timeouts.GIT_DEFAULT.value, 120)
        self.assertEqual(Timeouts.GIT_CHECKOUT.value, 60)
        self.assertEqual(Timeouts.TEST_DEFAULT.value, 300)

    def test_commit_types_enum(self):
        """Test CommitTypes enum values."""
        self.assertEqual(CommitTypes.FEAT.value, 'feat')
        self.assertEqual(CommitTypes.FIX.value, 'fix')
        self.assertEqual(CommitTypes.REFACTOR.value, 'refactor')

    def test_secret_patterns_enum(self):
        """Test SecretPatterns enum values."""
        patterns = [pattern.value for pattern in SecretPatterns]
        self.assertTrue(any('api[_-]?key' in p for p in patterns))
        self.assertTrue(any('secret' in p for p in patterns))
        self.assertTrue(any('password' in p for p in patterns))

    def test_validation_patterns_enum(self):
        """Test ValidationPatterns enum values."""
        self.assertEqual(ValidationPatterns.BRANCH_MAX_LENGTH.value, 255)
        self.assertEqual(ValidationPatterns.COMMIT_MAX_LENGTH.value, 72)

    def test_timeout_values_are_positive(self):
        """Test that all timeout values are positive."""
        for timeout in Timeouts:
            self.assertGreater(timeout.value, 0)

    def test_secret_patterns_are_regex(self):
        """Test that secret patterns are valid regex."""
        import re
        for pattern in SecretPatterns:
            try:
                re.compile(pattern.value)
            except re.error:
                self.fail(f"Pattern {pattern.name} is not valid regex")


class TestIntegration(unittest.TestCase):
    """Integration tests for utilities."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_root = Path(self.temp_dir)

        # Initialize git repo
        import subprocess
        subprocess.run(['git', 'init'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'checkout', '-b', 'main'], cwd=self.repo_root, capture_output=True)

        # Create schema directory
        self.schema_dir = self.repo_root / '.iflow' / 'schemas'
        self.schema_dir.mkdir(parents=True)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_git_command_with_validation(self):
        """Test git command followed by validation."""
        # Create a commit
        test_file = self.repo_root / 'test.txt'
        test_file.write_text('test content')

        import subprocess
        subprocess.run(['git', 'add', 'test.txt'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'test'], cwd=self.repo_root, capture_output=True)

        # Get current branch (should work)
        branch = get_current_branch(self.repo_root)
        self.assertEqual(branch, 'main')

        # Validate branch name
        is_valid, error = validate_branch_name(branch)
        self.assertTrue(is_valid)

    def test_schema_validation_with_file_lock(self):
        """Test schema validation combined with file locking."""
        # Create schema
        schema = {
            "version": "1.0.0",
            "required": ["id", "name"],
            "fields": {
                "id": {"type": "integer"},
                "name": {"type": "string"}
            }
        }
        schema_file = self.schema_dir / 'test-schema.json'
        schema_file.write_text(json.dumps(schema))

        # Create data file
        data_file = self.repo_root / 'data.json'
        data = {"id": 1, "name": "test"}
        data_file.write_text(json.dumps(data))

        # Use file lock while validating
        lock_file = self.repo_root / 'validation.lock'
        with FileLock(lock_file, timeout=1):
            validator = SchemaValidator(self.schema_dir)

            with open(data_file, 'r') as f:
                data = json.load(f)

            is_valid, errors = validator.validate(data, 'test-schema')

            self.assertTrue(is_valid)
            self.assertEqual(len(errors), 0)

    def test_multiple_validations_with_locking(self):
        """Test multiple validations with concurrent locking."""
        # Create schema
        schema = {
            "version": "1.0.0",
            "required": ["id"],
            "fields": {
                "id": {"type": "integer"}
            }
        }
        schema_file = self.schema_dir / 'concurrent-schema.json'
        schema_file.write_text(json.dumps(schema))

        lock_file = self.repo_root / 'concurrent.lock'
        results = []

        def validate_data(thread_id):
            try:
                with FileLock(lock_file, timeout=2):
                    validator = SchemaValidator(self.schema_dir)
                    data = {"id": thread_id}
                    is_valid, errors = validator.validate(data, 'concurrent-schema')
                    results.append((thread_id, is_valid))
            except FileLockError as e:
                results.append((thread_id, False))

        # Create multiple threads
        threads = [Thread(target=validate_data, args=(i,)) for i in range(5)]

        # Start threads
        for thread in threads:
            thread.start()

        # Wait for threads
        for thread in threads:
            thread.join()

        # All validations should succeed
        self.assertEqual(len(results), 5)
        self.assertTrue(all(is_valid for _, is_valid in results))


class TestInputSanitizer(unittest.TestCase):
    """Test input sanitizer functionality."""

    def test_sanitize_string_basic(self):
        """Test basic string sanitization."""
        result = InputSanitizer.sanitize_string("test string")
        self.assertEqual(result, "test string")

    def test_sanitize_string_null_bytes(self):
        """Test null byte removal."""
        result = InputSanitizer.sanitize_string("test\x00string")
        self.assertEqual(result, "teststring")
        self.assertNotIn('\x00', result)

    def test_sanitize_string_max_length(self):
        """Test max length validation."""
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_string("test", max_length=3)
        self.assertIn("maximum length", str(context.exception))

    def test_sanitize_string_allowed_chars(self):
        """Test allowed character filtering."""
        result = InputSanitizer.sanitize_string(
            "test-123",
            allowed_chars=r'[a-zA-Z0-9\-]'
        )
        self.assertEqual(result, "test-123")

    def test_sanitize_string_disallowed_chars(self):
        """Test disallowed character rejection."""
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_string(
                "test@123",
                allowed_chars=r'[a-zA-Z0-9]'
            )
        self.assertIn("disallowed characters", str(context.exception))

    def test_sanitize_string_non_string_input(self):
        """Test non-string input rejection."""
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_string(123)
        self.assertIn("must be a string", str(context.exception))

    def test_sanitize_branch_name_valid(self):
        """Test valid branch name sanitization."""
        test_cases = [
            "main",
            "feature/test",
            "bugfix/issue-123",
            "release/v1.0.0"
        ]

        for branch in test_cases:
            result = InputSanitizer.sanitize_branch_name(branch)
            self.assertEqual(result, branch)

    def test_sanitize_branch_name_start_with_dot(self):
        """Test branch name starting with dot is rejected."""
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_branch_name(".hidden")
        self.assertIn("cannot start or end with a dot", str(context.exception))

    def test_sanitize_branch_name_end_with_dot(self):
        """Test branch name ending with dot is rejected."""
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_branch_name("feature.")
        self.assertIn("cannot start or end with a dot", str(context.exception))

    def test_sanitize_branch_name_consecutive_dots(self):
        """Test branch name with consecutive dots is rejected."""
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_branch_name("feature..test")
        self.assertIn("cannot contain consecutive dots", str(context.exception))

    def test_sanitize_branch_name_at_brace(self):
        """Test branch name with @{ is rejected."""
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_branch_name("feature@{test")
        self.assertIn("cannot contain '@{'", str(context.exception))

    def test_sanitize_branch_name_lock_suffix(self):
        """Test branch name ending with .lock is rejected."""
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_branch_name("feature.lock")
        self.assertIn("cannot end with '.lock'", str(context.exception))

    def test_sanitize_commit_message_valid(self):
        """Test valid commit message sanitization."""
        result = InputSanitizer.sanitize_commit_message("Add new feature")
        self.assertEqual(result, "Add new feature")

    def test_sanitize_commit_message_command_injection(self):
        """Test commit message with command injection is rejected."""
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_commit_message("test; rm -rf /")
        self.assertIn("dangerous characters", str(context.exception))

    def test_sanitize_commit_message_max_length(self):
        """Test commit message max length."""
        long_message = "x" * 10001
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_commit_message(long_message)
        self.assertIn("maximum length", str(context.exception))

    def test_sanitize_file_path_valid(self):
        """Test valid file path sanitization."""
        result = InputSanitizer.sanitize_file_path("src/main.py")
        self.assertEqual(result, "src/main.py")

    def test_sanitize_file_path_traversal(self):
        """Test path traversal detection."""
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_file_path("../etc/passwd")
        self.assertIn("path traversal", str(context.exception))

    def test_sanitize_file_path_windows_traversal(self):
        """Test Windows path traversal detection."""
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_file_path("..\\windows\\system32")
        self.assertIn("path traversal", str(context.exception))

    def test_sanitize_file_path_tilde(self):
        """Test tilde expansion rejection."""
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_file_path("~/config")
        self.assertIn("Tilde expansion not allowed", str(context.exception))

    def test_sanitize_file_path_with_base_dir(self):
        """Test file path sanitization with base directory."""
        base_dir = Path("/tmp/test")
        result = InputSanitizer.sanitize_file_path("file.py", base_dir)
        self.assertIn("/tmp/test", result)

    def test_sanitize_file_path_absolute_outside_base(self):
        """Test absolute path outside base directory is rejected."""
        base_dir = Path("/tmp/test")
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_file_path("/etc/passwd", base_dir)
        self.assertIn("outside base directory", str(context.exception))

    def test_sanitize_username_valid(self):
        """Test valid username sanitization."""
        result = InputSanitizer.sanitize_username("john.doe")
        self.assertEqual(result, "john.doe")

    def test_sanitize_username_max_length(self):
        """Test username max length."""
        long_username = "x" * 101
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_username(long_username)
        self.assertIn("maximum length", str(context.exception))

    def test_sanitize_email_valid(self):
        """Test valid email sanitization."""
        result = InputSanitizer.sanitize_email("Test@Example.COM")
        self.assertEqual(result, "test@example.com")

    def test_sanitize_email_invalid_format(self):
        """Test invalid email format is rejected."""
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_email("invalid-email")
        self.assertIn("Invalid email format", str(context.exception))

    def test_check_command_injection_true(self):
        """Test command injection detection returns True."""
        test_cases = [
            "test; rm -rf /",
            "test && malicious",
            "test | cat",
            "test`whoami`",
            "$(cat /etc/passwd)"
        ]

        for test_input in test_cases:
            result = InputSanitizer.check_command_injection(test_input)
            self.assertTrue(result, f"Failed to detect injection in: {test_input}")

    def test_check_command_injection_false(self):
        """Test clean input returns False."""
        result = InputSanitizer.check_command_injection("normal text")
        self.assertFalse(result)

    def test_check_sql_injection_true(self):
        """Test SQL injection detection returns True."""
        test_cases = [
            "admin' OR '1'='1",
            "' OR 1=1 --",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM passwords"
        ]

        for test_input in test_cases:
            result = InputSanitizer.check_sql_injection(test_input)
            self.assertTrue(result, f"Failed to detect SQL injection in: {test_input}")

    def test_check_sql_injection_false(self):
        """Test clean input returns False."""
        result = InputSanitizer.check_sql_injection("normal text")
        self.assertFalse(result)

    def test_check_xss_true(self):
        """Test XSS detection returns True."""
        test_cases = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>"
        ]

        for test_input in test_cases:
            result = InputSanitizer.check_xss(test_input)
            self.assertTrue(result, f"Failed to detect XSS in: {test_input}")

    def test_check_xss_false(self):
        """Test clean input returns False."""
        result = InputSanitizer.check_xss("normal text")
        self.assertFalse(result)

    def test_sanitize_html(self):
        """Test HTML escaping."""
        result = InputSanitizer.sanitize_html("<script>alert('xss')</script>")
        self.assertEqual(result, "&lt;script&gt;alert('xss')&lt;/script&gt;")

    def test_sanitize_json_valid(self):
        """Test valid JSON sanitization."""
        input_json = '{"key": "value"}'
        result = InputSanitizer.sanitize_json(input_json)
        self.assertEqual(result, input_json)

    def test_sanitize_json_invalid(self):
        """Test invalid JSON is rejected."""
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_json("{invalid json}")
        self.assertIn("Invalid JSON", str(context.exception))

    def test_sanitize_list_valid(self):
        """Test list sanitization."""
        input_list = ["item1", "item2", "item3"]
        result = InputSanitizer.sanitize_list(input_list)
        self.assertEqual(result, input_list)

    def test_sanitize_list_non_list(self):
        """Test non-list input is rejected."""
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_list("not a list")
        self.assertIn("must be a list", str(context.exception))

    def test_sanitize_list_non_string_item(self):
        """Test list with non-string item is rejected."""
        with self.assertRaises(ValueError) as context:
            InputSanitizer.sanitize_list(["item1", 123, "item3"])
        self.assertIn("must be strings", str(context.exception))

    def test_sanitize_list_with_custom_sanitizer(self):
        """Test list with custom sanitizer."""
        input_list = ["item1", "item2", "item3"]
        result = InputSanitizer.sanitize_list(
            input_list,
            item_sanitizer=lambda x: x.upper()
        )
        self.assertEqual(result, ["ITEM1", "ITEM2", "ITEM3"])


class TestExceptions(unittest.TestCase):
    """Test exception classes and error codes."""

    def test_error_category_enum(self):
        """Test ErrorCategory enum values."""
        self.assertEqual(ErrorCategory.TRANSIENT.value, "transient")
        self.assertEqual(ErrorCategory.PERMANENT.value, "permanent")
        self.assertEqual(ErrorCategory.CONFIGURATION.value, "configuration")
        self.assertEqual(ErrorCategory.DEPENDENCY.value, "dependency")
        self.assertEqual(ErrorCategory.USER_ERROR.value, "user_error")
        self.assertEqual(ErrorCategory.SYSTEM_ERROR.value, "system_error")

    def test_error_code_success(self):
        """Test SUCCESS error code."""
        self.assertEqual(ErrorCode.SUCCESS.value, 0)

    def test_error_code_general_errors(self):
        """Test general error codes."""
        self.assertEqual(ErrorCode.UNKNOWN_ERROR.value, 1)
        self.assertEqual(ErrorCode.INVALID_INPUT.value, 2)
        self.assertEqual(ErrorCode.TIMEOUT.value, 4)
        self.assertEqual(ErrorCode.VALIDATION_ERROR.value, 5)

    def test_error_code_git_operations(self):
        """Test git operation error codes."""
        self.assertEqual(ErrorCode.GIT_NOT_FOUND.value, 10)
        self.assertEqual(ErrorCode.GIT_COMMAND_FAILED.value, 11)
        self.assertEqual(ErrorCode.GIT_REPOSITORY_NOT_FOUND.value, 12)
        self.assertEqual(ErrorCode.GIT_BRANCH_PROTECTED.value, 13)
        self.assertEqual(ErrorCode.GIT_MERGE_CONFLICT.value, 14)

    def test_error_code_file_operations(self):
        """Test file operation error codes."""
        self.assertEqual(ErrorCode.FILE_NOT_FOUND.value, 20)
        self.assertEqual(ErrorCode.FILE_READ_ERROR.value, 21)
        self.assertEqual(ErrorCode.FILE_WRITE_ERROR.value, 22)
        self.assertEqual(ErrorCode.INVALID_PATH.value, 23)
        self.assertEqual(ErrorCode.PATH_TRAVERSAL_DETECTED.value, 24)

    def test_error_code_state_configuration(self):
        """Test state/configuration error codes."""
        self.assertEqual(ErrorCode.CONFIG_NOT_FOUND.value, 30)
        self.assertEqual(ErrorCode.CONFIG_INVALID.value, 31)
        self.assertEqual(ErrorCode.STATE_CORRUPTED.value, 32)
        self.assertEqual(ErrorCode.SCHEMA_VALIDATION_FAILED.value, 34)

    def test_error_code_security(self):
        """Test security error codes."""
        self.assertEqual(ErrorCode.SECRET_DETECTED.value, 70)
        self.assertEqual(ErrorCode.SECURITY_VIOLATION.value, 71)
        self.assertEqual(ErrorCode.ACCESS_DENIED.value, 72)
        self.assertEqual(ErrorCode.AUTHENTICATION_FAILED.value, 73)

    def test_iflow_error_basic(self):
        """Test basic IFlowError creation."""
        error = IFlowError("Test error message")
        self.assertEqual(str(error), "[UNKNOWN_ERROR] Test error message")
        self.assertEqual(error.code, ErrorCode.UNKNOWN_ERROR)
        self.assertEqual(error.category, ErrorCategory.PERMANENT)

    def test_iflow_error_with_code(self):
        """Test IFlowError with custom error code."""
        error = IFlowError("Test error", code=ErrorCode.INVALID_INPUT)
        self.assertEqual(error.code, ErrorCode.INVALID_INPUT)

    def test_iflow_error_with_category(self):
        """Test IFlowError with custom category."""
        error = IFlowError("Test error", code=ErrorCode.UNKNOWN_ERROR, category=ErrorCategory.SYSTEM_ERROR)
        self.assertEqual(error.category, ErrorCategory.SYSTEM_ERROR)

    def test_iflow_error_with_details(self):
        """Test IFlowError with details."""
        details = {"file": "test.py", "line": 42}
        error = IFlowError("Test error", details=details)
        self.assertEqual(error.details, details)

    def test_validation_error(self):
        """Test ValidationError creation."""
        details = {"field": "username"}
        error = ValidationError("Invalid input", ErrorCode.VALIDATION_ERROR, details=details)
        self.assertEqual(error.details["field"], "username")
        self.assertEqual(error.code, ErrorCode.VALIDATION_ERROR)
        self.assertEqual(error.category, ErrorCategory.USER_ERROR)

    def test_git_error(self):
        """Test GitError creation."""
        details = {"command": "git status"}
        error = GitError("Git command failed", ErrorCode.GIT_COMMAND_FAILED, details=details)
        self.assertEqual(error.details["command"], "git status")
        self.assertEqual(error.code, ErrorCode.GIT_COMMAND_FAILED)
        self.assertEqual(error.category, ErrorCategory.TRANSIENT)


if __name__ == '__main__':
    unittest.main()
