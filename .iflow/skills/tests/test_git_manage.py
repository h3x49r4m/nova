#!/usr/bin/env python3
"""
Test suite for git-manage.py
Tests git operations, commit handling, and safety checks.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from git_manage.git_manage import GitManage
# Import exceptions and constants from utils
from utils import (
    ErrorCode,
    CommitTypes,
    CoverageThresholds,
    DEFAULT_PROTECTED_BRANCHES
)


class TestGitManage(unittest.TestCase):
    """Test GitManage class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_root = Path(self.temp_dir)
        self.config_dir = self.repo_root / '.iflow' / 'skills' / 'git-manage'
        self.config_dir.mkdir(parents=True)

        # Create config file
        self.config_file = self.config_dir / 'config.json'
        self.config_file.write_text(json.dumps({
            'pre_commit_checks': True,
            'run_tests': False,  # Disabled for tests
            'check_coverage': False,  # Disabled for tests
            'detect_secrets': True,
            'branch_protection': True,
            'protected_branches': DEFAULT_PROTECTED_BRANCHES.copy(),
            'coverage_threshold': CoverageThresholds.LINES.value,
            'coverage_thresholds': {
                'lines': CoverageThresholds.LINES.value,
                'branches': CoverageThresholds.BRANCHES.value
            },
            'strict_validation': False  # Disable schema validation in tests
        }))

        # Initialize git repo
        import subprocess
        subprocess.run(['git', 'init'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.repo_root, capture_output=True)
        subprocess.run(['git', 'checkout', '-b', 'main'], cwd=self.repo_root, capture_output=True)

        # Create a test file
        self.test_file = self.repo_root / 'test.txt'
        self.test_file.write_text('test content')

        self.git_manage = GitManage(self.repo_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_git_manage_initialization(self):
        """Test GitManage initialization."""
        self.assertIsNotNone(self.git_manage)
        self.assertEqual(self.git_manage.repo_root, self.repo_root)
        self.assertIsNotNone(self.git_manage.config)
        self.assertTrue(self.git_manage.config['detect_secrets'])

    def test_get_current_branch(self):
        """Test getting current branch."""
        branch = self.git_manage.get_current_branch()
        self.assertEqual(branch, 'main')

    def test_get_staged_files_empty(self):
        """Test getting staged files when none are staged."""
        files = self.git_manage.get_staged_files()
        self.assertEqual(files, [])

    def test_get_staged_files(self):
        """Test getting staged files."""
        # Stage a file
        import subprocess
        subprocess.run(['git', 'add', 'test.txt'], cwd=self.repo_root, capture_output=True)

        files = self.git_manage.get_staged_files()
        self.assertEqual(len(files), 1)
        self.assertIn('test.txt', files[0])

    def test_get_unstaged_files(self):
        """Test getting unstaged files."""
        # Modify test file
        self.test_file.write_text('modified content')

        files = self.git_manage.get_unstaged_files()
        self.assertEqual(len(files), 1)
        self.assertIn('test.txt', files[0])

    def test_detect_secrets(self):
        """Test secret detection."""
        # Create a file with a secret
        secret_file = self.repo_root / 'secret.py'
        secret_file.write_text('API_KEY = "sk_test_1234567890abcdefghijklmnopqrstuvwxyz"')

        has_secrets, secrets = self.git_manage.detect_secrets(['secret.py'])

        self.assertTrue(has_secrets)
        self.assertTrue(any('secret.py' in s for s in secrets))

    def test_detect_secrets_no_secrets(self):
        """Test secret detection with no secrets."""
        # Create a file without secrets
        safe_file = self.repo_root / 'safe.py'
        safe_file.write_text('API_URL = "https://api.example.com"')

        has_secrets, secrets = self.git_manage.detect_secrets(['safe.py'])

        self.assertFalse(has_secrets)
        self.assertEqual(len(secrets), 0)

    @patch('git_manage.git_manage.subprocess.run')
    def test_run_tests_disabled(self, mock_run):
        """Test running tests when disabled."""
        self.git_manage.config['run_tests'] = False

        code, output = self.git_manage.run_tests()

        self.assertEqual(code, 0)
        self.assertIn('skipped', output)
        mock_run.assert_not_called()

    @patch('git_manage.git_manage.subprocess.run')
    def test_run_tests_pytest_not_available(self, mock_run):
        """Test running tests when pytest not available."""
        mock_run.side_effect = FileNotFoundError()

        code, output = self.git_manage.run_tests()

        self.assertEqual(code, 0)
        self.assertIn('pytest not available', output)

    @patch('git_manage.git_manage.subprocess.run')
    def test_run_tests_success(self, mock_run):
        """Test running tests successfully."""
        # Mock pytest version check and test run
        mock_run.side_effect = [
            Mock(returncode=0),  # pytest --version
            Mock(returncode=0, stdout='tests passed')
        ]

        code, output = self.git_manage.run_tests()

        self.assertEqual(code, 0)
        self.assertIn('tests passed', output)

    @patch('git_manage.git_manage.subprocess.run')
    def test_run_tests_failure(self, mock_run):
        """Test running tests with failures."""
        mock_run.side_effect = [
            Mock(returncode=0),  # pytest --version
            Mock(returncode=1, stdout='tests failed')
        ]

        code, output = self.git_manage.run_tests()

        self.assertEqual(code, 1)
        self.assertIn('tests failed', output)

    def test_check_coverage_disabled(self):
        """Test checking coverage when disabled."""
        self.git_manage.config['check_coverage'] = False

        code, line_cov, branch_cov = self.git_manage.check_coverage()

        self.assertEqual(code, 0)
        self.assertEqual(line_cov, 100.0)
        self.assertEqual(branch_cov, 100.0)

    def test_check_branch_protected(self):
        """Test checking if branch is protected."""
        protected, msg = self.git_manage.check_branch_protection()

        # On main branch, should be protected
        self.assertTrue(protected)
        self.assertIn('protected', msg.lower())

    def test_parse_commit_message_valid(self):
        """Test parsing a valid conventional commit message."""
        message = "feat(auth): add user authentication"
        parsed = self.git_manage.parse_commit_message(message)

        self.assertTrue(parsed['valid'])
        self.assertEqual(parsed['type'], 'feat')
        self.assertEqual(parsed['scope'], 'auth')
        self.assertEqual(parsed['description'], 'add user authentication')

    def test_parse_commit_message_invalid(self):
        """Test parsing an invalid commit message."""
        message = "just a regular message"
        parsed = self.git_manage.parse_commit_message(message)

        self.assertFalse(parsed['valid'])

    def test_generate_commit_message_with_scope(self):
        """Test generating commit message with scope."""
        message = self.git_manage.generate_commit_message(
            'feat', 'auth', 'add authentication',
            body='Changes:\n- Added login form\n- Added token validation',
            files_changed=['auth.py', 'login.html'],
            test_results='passed',
            coverage=85.0
        )

        self.assertIn('feat[auth]:', message)
        self.assertIn('Changes:', message)
        self.assertIn('- Added login form', message)
        self.assertIn('Files changed:', message)
        self.assertIn('Tests: passed', message)
        self.assertIn('Coverage: 85.0%', message)

    def test_generate_commit_message_without_scope(self):
        """Test generating commit message without scope."""
        message = self.git_manage.generate_commit_message(
            'fix', None, 'fix bug in auth',
            files_changed=['auth.py']
        )

        self.assertIn('fix: fix bug in auth', message)
        self.assertIn('Files changed:', message)

    @patch('git_manage.git_manage.run_git_command')
    def test_commit_no_changes(self, mock_run_git):
        """Test committing when there are no staged changes."""
        mock_run_git.return_value = (0, '', '')  # No staged files

        code, output = self.git_manage.commit('feat', None, 'test')

        self.assertEqual(code, ErrorCode.INVALID_INPUT.value)
        self.assertIn('No changes to commit', output)

    @patch('git_manage.git_manage.run_git_command')
    def test_commit_invalid_type(self, mock_run_git):
        """Test committing with invalid commit type."""
        mock_run_git.return_value = (0, 'test.txt', '')  # One staged file

        code, output = self.git_manage.commit('invalid', None, 'test')

        self.assertEqual(code, ErrorCode.INVALID_INPUT.value)
        self.assertIn('Invalid commit type', output)

    @patch('git_manage.git_manage.run_git_command')
    def test_commit_protected_branch(self, mock_run_git):
        """Test committing to a protected branch."""
        mock_run_git.return_value = (0, 'test.txt', '')  # Staged file
        self.git_manage.config['auto_create_branch'] = False

        code, output = self.git_manage.commit('feat', None, 'test')

        self.assertEqual(code, ErrorCode.GIT_BRANCH_PROTECTED.value)
        self.assertIn('protected', output.lower())

    @patch('git_manage.git_manage.run_git_command')
    def test_commit_secret_detected(self, mock_run_git):
        """Test committing when secrets are detected."""
        # Mock staged files
        mock_run_git.return_value = (0, 'secret.py', '')

        # Mock secret detection
        with patch.object(self.git_manage, 'detect_secrets', return_value=(True, ['secret.py: matches pattern'])):
            code, output = self.git_manage.commit('feat', None, 'test')

            self.assertEqual(code, ErrorCode.SECRET_DETECTED.value)
            self.assertIn('Secrets detected', output)

    @patch('git_manage.git_manage.run_git_command')
    def test_commit_success(self, mock_run_git):
        """Test successful commit."""
        # Mock staged files
        mock_run_git.return_value = (0, 'test.txt', '')

        # Disable pre-commit checks for this test
        self.git_manage.config['pre_commit_checks'] = False

        code, output = self.git_manage.commit('feat', None, 'test', no_verify=True)

        self.assertEqual(code, ErrorCode.SUCCESS.value)
        self.assertIn('Commit successful', output)

    def test_commit_invalid_body_no_changes_section(self):
        """Test commit validation fails without Changes section."""
        code, output = self.git_manage.commit(
            'feat', None, 'test',
            body='Just a regular body without Changes section'
        )

        self.assertEqual(code, ErrorCode.VALIDATION_FAILED.value)
        self.assertIn('Changes:', output)

    def test_commit_invalid_body_no_bullet_points(self):
        """Test commit validation fails without bullet points."""
        code, output = self.git_manage.commit(
            'feat', None, 'test',
            body='Changes:\nNo bullet points here'
        )

        self.assertEqual(code, ErrorCode.VALIDATION_FAILED.value)
        self.assertIn('bullet point', output)

    @patch('git_manage.git_manage.run_git_command')
    def test_add_files(self, mock_run_git):
        """Test adding files."""
        mock_run_git.return_value = (0, '', '')

        code, output = self.git_manage.add_files(['test.txt'])

        self.assertEqual(code, 0)
        self.assertIn('Staged', output)
        mock_run_git.assert_called_once()

    @patch('git_manage.git_manage.run_git_command')
    def test_add_files_no_files(self, mock_run_git):
        """Test adding files when no files specified."""
        code, output = self.git_manage.add_files([])

        self.assertEqual(code, 1)
        self.assertIn('No files', output)
        mock_run_git.assert_not_called()

    @patch('git_manage.git_manage.run_git_command')
    def test_get_file_diffs(self, mock_run_git):
        """Test getting file diffs."""
        mock_run_git.return_value = (0, 'diff content', '')

        diff = self.git_manage.get_file_diffs(['test.txt'])

        self.assertEqual(diff, 'diff content')
        mock_run_git.assert_called_once_with(['diff', '--cached', 'test.txt'])

    @patch('git_manage.git_manage.run_git_command')
    def test_status_clean(self, mock_run_git):
        """Test git status when clean."""
        mock_run_git.return_value = (0, '', '')

        code, output = self.git_manage.status()

        self.assertEqual(code, 0)
        self.assertIn('clean', output)

    @patch('git_manage.git_manage.run_git_command')
    def test_status_with_changes(self, mock_run_git):
        """Test git status with changes."""
        mock_run_git.return_value = (0, 'M test.txt\n?? new.txt', '')

        code, output = self.git_manage.status()

        self.assertEqual(code, 0)
        self.assertIn('M test.txt', output)
        self.assertIn('?? new.txt', output)

    @patch('git_manage.git_manage.run_git_command')
    def test_diff(self, mock_run_git):
        """Test getting diff."""
        mock_run_git.return_value = (0, 'diff content', '')

        code, output = self.git_manage.diff()

        self.assertEqual(code, 0)
        self.assertEqual(output, 'diff content')
        mock_run_git.assert_called_once_with(['diff'])

    @patch('git_manage.git_manage.run_git_command')
    def test_diff_staged(self, mock_run_git):
        """Test getting staged diff."""
        mock_run_git.return_value = (0, 'staged diff', '')

        code, output = self.git_manage.diff(staged=True)

        self.assertEqual(code, 0)
        self.assertEqual(output, 'staged diff')
        mock_run_git.assert_called_once_with(['diff', '--cached'])

    @patch('git_manage.git_manage.run_git_command')
    def test_log(self, mock_run_git):
        """Test getting commit log."""
        mock_run_git.return_value = (0, 'abc123 Initial commit\ndef456 Second commit', '')

        code, output = self.git_manage.log(count=10)

        self.assertEqual(code, 0)
        self.assertIn('abc123', output)
        self.assertIn('def456', output)

    @patch('git_manage.git_manage.run_git_command')
    def test_undo_soft(self, mock_run_git):
        """Test soft undo."""
        mock_run_git.return_value = (0, '', '')

        code, output = self.git_manage.undo('soft')

        self.assertEqual(code, 0)
        self.assertIn('successful', output)
        self.assertIn('soft', output)

    @patch('git_manage.git_manage.run_git_command')
    def test_undo_hard(self, mock_run_git):
        """Test hard undo."""
        mock_run_git.return_value = (0, '', '')

        code, output = self.git_manage.undo('hard')

        self.assertEqual(code, 0)
        self.assertIn('successful', output)
        self.assertIn('hard', output)

    @patch('git_manage.git_manage.run_git_command')
    def test_undo_invalid_mode(self, mock_run_git):
        """Test undo with invalid mode."""
        code, output = self.git_manage.undo('invalid')

        self.assertEqual(code, 1)
        self.assertIn('Invalid mode', output)
        mock_run_git.assert_not_called()

    @patch('git_manage.git_manage.run_git_command')
    def test_amend_no_description(self, mock_run_git):
        """Test amending commit without description."""
        mock_run_git.side_effect = [
            (0, 'original message\n', ''),  # log
            (0, '', '')  # amend
        ]

        code, output = self.git_manage.amend()

        self.assertEqual(code, 0)
        self.assertIn('successful', output)

    @patch('git_manage.git_manage.run_git_command')
    def test_amend_with_description(self, mock_run_git):
        """Test amending commit with description."""
        mock_run_git.side_effect = [
            (0, 'original message\n', ''),  # log
            (0, '', '')  # amend
        ]

        code, output = self.git_manage.amend('additional info')

        self.assertEqual(code, 0)
        self.assertIn('successful', output)

    @patch('git_manage.git_manage.run_git_command')
    def test_stash_save(self, mock_run_git):
        """Test saving stash."""
        mock_run_git.return_value = (0, '', '')

        code, output = self.git_manage.stash('save', 'test message')

        self.assertEqual(code, 0)
        self.assertIn('save successful', output)

    @patch('git_manage.git_manage.run_git_command')
    def test_stash_pop(self, mock_run_git):
        """Test popping stash."""
        mock_run_git.return_value = (0, '', '')

        code, output = self.git_manage.stash('pop')

        self.assertEqual(code, 0)
        self.assertIn('pop successful', output)

    @patch('git_manage.git_manage.run_git_command')
    def test_stash_list(self, mock_run_git):
        """Test listing stashes."""
        mock_run_git.return_value = (0, 'stash@{0}: WIP on main\nstash@{1}: Other stash', '')

        code, output = self.git_manage.stash('list')

        self.assertEqual(code, 0)
        self.assertIn('stash@{0}', output)

    @patch('git_manage.git_manage.run_git_command')
    def test_stash_drop(self, mock_run_git):
        """Test dropping stash."""
        mock_run_git.return_value = (0, '', '')

        code, output = self.git_manage.stash('drop')

        self.assertEqual(code, 0)
        self.assertIn('drop successful', output)

    @patch('git_manage.git_manage.run_git_command')
    def test_push(self, mock_run_git):
        """Test pushing to remote."""
        mock_run_git.return_value = (0, '', '')

        code, output = self.git_manage.push('origin', 'feature-branch')

        self.assertEqual(code, 0)
        self.assertIn('Pushed', output)
        self.assertIn('origin/feature-branch', output)


class TestGitManageConfig(unittest.TestCase):
    """Test GitManage configuration."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_root = Path(self.temp_dir)
        self.config_dir = self.repo_root / '.iflow' / 'skills' / 'git-manage'
        self.config_dir.mkdir(parents=True)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_load_config_default(self):
        """Test loading default config when no config file exists."""
        git_manage = GitManage(self.repo_root)

        self.assertIsNotNone(git_manage.config)
        self.assertIn('pre_commit_checks', git_manage.config)
        self.assertIn('protected_branches', git_manage.config)

    def test_load_config_from_file(self):
        """Test loading config from file."""
        custom_config = {
            'pre_commit_checks': False,
            'run_tests': False,
            'check_coverage': False,
            'detect_secrets': False,
            'branch_protection': False,
            'protected_branches': ['custom-main'],
            'coverage_threshold': 90
        }
        config_file = self.config_dir / 'config.json'
        config_file.write_text(json.dumps(custom_config))

        git_manage = GitManage(self.repo_root)

        self.assertEqual(git_manage.config['pre_commit_checks'], False)
        self.assertEqual(git_manage.config['coverage_threshold'], 90)
        self.assertEqual(git_manage.config['protected_branches'], ['custom-main'])

    def test_load_config_merge(self):
        """Test that user config merges with defaults."""
        custom_config = {
            'run_tests': False,
            'custom_field': 'custom_value'
        }
        config_file = self.config_dir / 'config.json'
        config_file.write_text(json.dumps(custom_config))

        git_manage = GitManage(self.repo_root)

        # Should have custom value
        self.assertEqual(git_manage.config['run_tests'], False)
        self.assertEqual(git_manage.config['custom_field'], 'custom_value')

        # Should still have defaults
        self.assertIn('pre_commit_checks', git_manage.config)
        self.assertIn('detect_secrets', git_manage.config)

    def test_load_config_invalid_json(self):
        """Test loading invalid JSON config."""
        config_file = self.config_dir / 'config.json'
        config_file.write_text('invalid json')

        git_manage = GitManage(self.repo_root)

        # Should fall back to defaults
        self.assertIsNotNone(git_manage.config)
        self.assertIn('pre_commit_checks', git_manage.config)


class TestGitManageConstants(unittest.TestCase):
    """Test that GitManage uses constants correctly."""

    def test_commit_types_from_constants(self):
        """Test that commit types come from constants."""
        import tempfile
        import shutil

        temp_dir = tempfile.mkdtemp()
        try:
            repo_root = Path(temp_dir)
            config_dir = repo_root / '.iflow' / 'skills' / 'git-manage'
            config_dir.mkdir(parents=True)
            (config_dir / 'config.json').write_text('{}')

            git_manage = GitManage(repo_root)

            # Check that commit types match constants
            for commit_type in CommitTypes:
                self.assertIn(commit_type.value, git_manage.COMMIT_TYPES)

        finally:
            shutil.rmtree(temp_dir)

    def test_secret_patterns_from_constants(self):
        """Test that secret patterns come from constants."""
        import tempfile
        import shutil

        temp_dir = tempfile.mkdtemp()
        try:
            repo_root = Path(temp_dir)
            config_dir = repo_root / '.iflow' / 'skills' / 'git-manage'
            config_dir.mkdir(parents=True)
            (config_dir / 'config.json').write_text('{}')

            git_manage = GitManage(repo_root)

            # Check that secret patterns match constants
            self.assertEqual(len(git_manage.SECRET_PATTERNS), len(SecretPatterns))

        finally:
            shutil.rmtree(temp_dir)


if __name__ == '__main__':
    unittest.main()