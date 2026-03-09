#!/usr/bin/env python3
"""
Test suite for input_sanitizer.py
Tests input validation and sanitization to prevent injection attacks.
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import InputSanitizer


class TestInputSanitizer(unittest.TestCase):
    """Test cases for InputSanitizer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.sanitizer = InputSanitizer()

    def test_sanitize_html(self):
        """Test HTML sanitization."""
        # Test basic HTML tags - InputSanitizer sanitizes by escaping HTML
        result1 = self.sanitizer.sanitize_html("<script>alert('xss')</script>")
        # Should escape the script tags
        self.assertNotIn("<script>", result1)
        self.assertIn("&lt;", result1)

        result2 = self.sanitizer.sanitize_html("<b>bold</b>")
        self.assertNotIn("<b>", result2)

        # Test plain text
        result3 = self.sanitizer.sanitize_html("plain text")
        self.assertEqual(result3, "plain text")

    def test_check_sql_injection(self):
        """Test SQL injection detection."""
        # Test SQL injection patterns
        self.assertTrue(self.sanitizer.check_sql_injection("' OR '1'='1"))
        self.assertTrue(self.sanitizer.check_sql_injection("'; DROP TABLE users; --"))
        # UNION requires semicolon in the pattern
        self.assertTrue(self.sanitizer.check_sql_injection("; UNION SELECT * FROM users"))

        # Test safe SQL
        self.assertFalse(self.sanitizer.check_sql_injection("SELECT * FROM users WHERE id = ?"))
        self.assertFalse(self.sanitizer.check_sql_injection("John Doe"))

    def test_check_command_injection(self):
        """Test command injection detection."""
        # Test command injection patterns
        self.assertTrue(self.sanitizer.check_command_injection("; rm -rf /"))
        self.assertTrue(self.sanitizer.check_command_injection("&& cat /etc/passwd"))
        self.assertTrue(self.sanitizer.check_command_injection("| ls -la"))
        self.assertTrue(self.sanitizer.check_command_injection("`whoami`"))
        self.assertTrue(self.sanitizer.check_command_injection("$(date)"))

        # Test safe commands
        self.assertFalse(self.sanitizer.check_command_injection("filename.txt"))
        self.assertFalse(self.sanitizer.check_command_injection("my-file"))

    def test_check_xss(self):
        """Test XSS detection."""
        # Test XSS patterns
        self.assertTrue(self.sanitizer.check_xss("<script>alert('xss')</script>"))
        self.assertTrue(self.sanitizer.check_xss("<img src=x onerror=alert('xss')>"))
        self.assertTrue(self.sanitizer.check_xss("<svg onload=alert('xss')>"))
        self.assertTrue(self.sanitizer.check_xss("javascript:alert('xss')"))

        # Test safe HTML
        self.assertFalse(self.sanitizer.check_xss("<p>Hello World</p>"))
        self.assertFalse(self.sanitizer.check_xss("plain text"))

    def test_sanitize_json_string(self):
        """Test JSON string sanitization."""
        # Test JSON string validation and re-serialization
        json_str = '{"name": "test", "age": 30}'
        sanitized = self.sanitizer.sanitize_json(json_str)
        # Should re-serialize the JSON
        self.assertEqual(sanitized, json_str)

        # Test invalid JSON
        with self.assertRaises(ValueError):
            self.sanitizer.sanitize_json("invalid json")

    def test_sanitize_list_strings(self):
        """Test list string sanitization."""
        # Test list with item sanitizer
        input_list = ["  test  ", "  safe text  ", "  bold  "]

        # Provide a sanitizer function
        def strip_whitespace(s):
            return s.strip()

        sanitized = self.sanitizer.sanitize_list(input_list, item_sanitizer=strip_whitespace)
        self.assertEqual(sanitized[0], "test")
        self.assertEqual(sanitized[1], "safe text")
        self.assertEqual(sanitized[2], "bold")

    def test_sanitize_email(self):
        """Test email sanitization."""
        # Valid emails
        result1 = self.sanitizer.sanitize_email("test@example.com")
        self.assertEqual(result1, "test@example.com")

        result2 = self.sanitizer.sanitize_email("user.name@domain.co.uk")
        self.assertEqual(result2, "user.name@domain.co.uk")

    def test_sanitize_file_path(self):
        """Test file path sanitization."""
        # Valid paths
        result1 = self.sanitizer.sanitize_file_path("file.txt")
        self.assertEqual(result1, "file.txt")

        result2 = self.sanitizer.sanitize_file_path("my-file_123.txt")
        self.assertEqual(result2, "my-file_123.txt")

        # Path traversal - should raise ValueError
        with self.assertRaises(ValueError):
            self.sanitizer.sanitize_file_path("../etc/passwd")

        with self.assertRaises(ValueError):
            self.sanitizer.sanitize_file_path("../../secret")

        # Absolute paths are allowed
        result3 = self.sanitizer.sanitize_file_path("/etc/passwd")
        self.assertEqual(result3, "/etc/passwd")

    def test_sanitize_string(self):
        """Test string sanitization."""
        # Test basic sanitization
        result1 = self.sanitizer.sanitize_string("  test  ")
        self.assertEqual(result1, "test")

        result2 = self.sanitizer.sanitize_string("test\nwith\nnewlines")
        self.assertEqual(result2, "test\nwith\nnewlines")

        result3 = self.sanitizer.sanitize_string("test\twith\ttabs")
        self.assertEqual(result3, "test\twith\ttabs")


if __name__ == '__main__':
    unittest.main()