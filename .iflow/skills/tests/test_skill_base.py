#!/usr/bin/env python3
"""
Test suite for skill_base.py
Tests the base class for all skill implementations.
"""

import json
import tempfile
import unittest
from pathlib import Path

from utils.skill_base import SkillBase
from utils.exceptions import IFlowError, ErrorCode, ValidationError


class TestSkillBase(unittest.TestCase):
    """Test SkillBase class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.skills_dir = self.temp_dir / '.iflow' / 'skills'
        self.skills_dir.mkdir(parents=True)
        self.logs_dir = self.temp_dir / '.iflow' / 'logs'
        self.logs_dir.mkdir(parents=True)
        self.state_dir = self.temp_dir / '.state'
        self.state_dir.mkdir(parents=True)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_skill_initialization(self):
        """Test skill initialization with default parameters."""
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        self.assertEqual(skill.skill_name, 'test-skill')
        self.assertEqual(skill.repo_root, self.temp_dir)
        self.assertIsNotNone(skill.logger)
        self.assertIsInstance(skill.config, dict)
    
    def test_skill_initialization_with_custom_repo(self):
        """Test skill initialization with custom repo root."""
        custom_dir = Path(tempfile.mkdtemp())
        try:
            skill = MockSkill(skill_name='test-skill', repo_root=custom_dir)
            
            self.assertEqual(skill.repo_root, custom_dir)
        finally:
            import shutil
            if custom_dir.exists():
                shutil.rmtree(custom_dir)
    
    def test_get_default_config(self):
        """Test getting default configuration."""
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        default_config = skill.get_default_config()
        
        self.assertIsInstance(default_config, dict)
        self.assertIn('version', default_config)
        self.assertIn('auto_commit', default_config)
    
    def test_load_config_default(self):
        """Test loading default configuration when no config file exists."""
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        # No config file should exist
        config_file = skill.config_file
        self.assertFalse(config_file.exists())
        
        # Config should have defaults
        self.assertIn('version', skill.config)
        self.assertIn('auto_commit', skill.config)
        self.assertEqual(skill.config['auto_commit'], True)
    
    def test_load_config_from_file(self):
        """Test loading configuration from file."""
        skill_dir = self.temp_dir / '.iflow' / 'skills' / 'test-skill'
        skill_dir.mkdir(parents=True)
        config_file = skill_dir / 'config.json'
        
        # Write test config with required fields
        test_config = {
            'name': 'test-skill',
            'version': '2.0.0',
            'type': 'role',
            'description': 'Test skill for testing',
            'auto_commit': False,
            'custom_setting': 'custom_value'
        }
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
        
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        # Config should be loaded and merged with defaults
        self.assertEqual(skill.config['version'], '2.0.0')
        self.assertEqual(skill.config['auto_commit'], False)
        self.assertEqual(skill.config['custom_setting'], 'custom_value')
    
    def test_load_config_invalid_json(self):
        """Test loading configuration with invalid JSON."""
        skill_dir = self.temp_dir / '.iflow' / 'skills' / 'test-skill'
        skill_dir.mkdir(parents=True)
        config_file = skill_dir / 'config.json'
        
        # Write invalid JSON
        with open(config_file, 'w') as f:
            f.write('{invalid json}')
        
        # Should not raise exception, just log warning
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        # Should have defaults
        self.assertIn('version', skill.config)
    
    def test_save_config(self):
        """Test saving configuration to file."""
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        # Add required fields and modify config
        skill.config['name'] = 'test-skill'
        skill.config['type'] = 'role'
        skill.config['description'] = 'Test skill for testing'
        skill.config['custom_value'] = 'test'
        
        # Save config
        code, message = skill.save_config()
        
        self.assertEqual(code, 0)
        self.assertIn('saved', message.lower())
        
        # Verify file was created
        self.assertTrue(skill.config_file.exists())
        
        # Verify content
        with open(skill.config_file, 'r') as f:
            saved_config = json.load(f)
        self.assertEqual(saved_config['custom_value'], 'test')
    
    def test_get_state_dir(self):
        """Test getting state directory."""
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        # Default state directory
        state_dir = skill.get_state_dir()
        self.assertEqual(state_dir, self.temp_dir / '.state')
    
    def test_get_state_dir_shared_state(self):
        """Test getting state directory with shared state."""
        # Remove .state directory so shared state takes precedence
        if self.state_dir.exists():
            import shutil
            shutil.rmtree(self.state_dir)
        
        # Create shared state directory
        shared_state = self.temp_dir / '.iflow' / 'skills' / '.shared-state'
        shared_state.mkdir(parents=True)
        
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        state_dir = skill.get_state_dir()
        self.assertEqual(state_dir, shared_state)
    
    def test_read_state_file(self):
        """Test reading a state file."""
        # Create test state file
        state_file = self.state_dir / 'test-state.md'
        test_content = 'Test state content'
        with open(state_file, 'w') as f:
            f.write(test_content)
        
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        code, content = skill.read_state_file('test-state.md')
        
        self.assertEqual(code, 0)
        self.assertEqual(content, test_content)
    
    def test_read_state_file_not_found(self):
        """Test reading a non-existent state file."""
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        code, message = skill.read_state_file('nonexistent.md')
        
        self.assertEqual(code, ErrorCode.FILE_NOT_FOUND.value)
        self.assertIn('not found', message.lower())
    
    def test_write_state_file(self):
        """Test writing a state file."""
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        test_content = 'Test content to write'
        code, message = skill.write_state_file('test-write.md', test_content)
        
        self.assertEqual(code, 0)
        self.assertIn('written', message.lower())
        
        # Verify file was created
        state_file = self.state_dir / 'test-write.md'
        self.assertTrue(state_file.exists())
        
        # Verify content
        with open(state_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, test_content)
    
    def test_write_state_file_creates_dir(self):
        """Test writing a state file creates directory if needed."""
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        # Remove state directory
        if self.state_dir.exists():
            import shutil
            shutil.rmtree(self.state_dir)
        
        # Write file (should create directory)
        code, message = skill.write_state_file('test.md', 'content')
        
        self.assertEqual(code, 0)
        self.assertTrue(self.state_dir.exists())
    
    def test_get_state_contracts(self):
        """Test getting state contracts."""
        # Create SKILL.md file with contracts
        skill_dir = self.temp_dir / '.iflow' / 'skills' / 'test-skill'
        skill_dir.mkdir(parents=True)
        skill_md = skill_dir / 'SKILL.md'
        
        skill_md_content = """
# Test Skill

## State Contracts

### Read
- `test-read.md`

### Write
- `test-write.md`
"""
        with open(skill_md, 'w') as f:
            f.write(skill_md_content)
        
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        contracts = skill.get_state_contracts()
        
        self.assertIn('test-read.md', contracts['read'])
        self.assertIn('test-write.md', contracts['write'])
    
    def test_log_workflow_start(self):
        """Test logging workflow start."""
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        # Should not raise exception
        skill.log_workflow_start('test-workflow', param1='value1')
    
    def test_log_workflow_complete(self):
        """Test logging workflow complete."""
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        # Should not raise exception
        skill.log_workflow_complete('test-workflow', 1.5, result='success')
    
    def test_log_error(self):
        """Test logging errors."""
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        error = Exception('Test error')
        context = {'param': 'value'}
        
        # Should not raise exception
        skill.log_error(error, context)
    
    def test_handle_error_iflow_error(self):
        """Test handling IFlowError."""
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        error = IFlowError(message='Test error', code=ErrorCode.VALIDATION_ERROR)
        code, message = skill.handle_error(error)
        
        self.assertEqual(code, ErrorCode.VALIDATION_ERROR.value)
        self.assertIn('Test error', message)
    
    def test_handle_error_validation_error(self):
        """Test handling ValidationError."""
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        error = ValidationError(message='Validation failed', code=ErrorCode.VALIDATION_ERROR)
        code, message = skill.handle_error(error)
        
        self.assertEqual(code, ErrorCode.VALIDATION_ERROR.value)
        self.assertIn('Validation failed', message)
    
    def test_handle_error_generic_error(self):
        """Test handling generic error."""
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        error = Exception('Generic error')
        code, message = skill.handle_error(error)
        
        self.assertEqual(code, ErrorCode.UNKNOWN_ERROR.value)
        self.assertEqual(message, 'Generic error')
    
    def test_repr(self):
        """Test string representation."""
        skill = MockSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        repr_str = repr(skill)
        
        self.assertIn('MockSkill', repr_str)
        self.assertIn('test-skill', repr_str)
        self.assertIn(str(self.temp_dir), repr_str)
    
    def test_run_workflow_not_implemented(self):
        """Test that run_workflow raises NotImplementedError."""
        # Create SkillBase directly (not MockSkill which overrides run_workflow)
        from utils.skill_base import SkillBase as BaseSkill
        
        skill = BaseSkill(skill_name='test-skill', repo_root=self.temp_dir)
        
        with self.assertRaises(NotImplementedError):
            skill.run_workflow(self.temp_dir, 'test-workflow')


class MockSkill(SkillBase):
    """Mock skill for testing SkillBase."""

    def get_default_config(self):
        """Get default config for testing."""
        return {
            'version': '1.0.0',
            'auto_commit': True,
            'test_mode': True
        }

    def run_workflow(self, project_path, workflow_name, **kwargs):
        """Override for testing."""
        return 0, f"Workflow {workflow_name} executed"


if __name__ == '__main__':
    unittest.main()