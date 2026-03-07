#!/usr/bin/env python3
"""
Unit tests for DocumentValidator module.
"""

import json
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
utils_path = Path(__file__).parent.parent / 'utils'
sys.path.insert(0, str(utils_path))

from document_validator import DocumentValidator
from exceptions import IFlowError, ValidationError, ErrorCode


class TestDocumentValidator:
    """Tests for the DocumentValidator class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def document_validator(self, temp_dir):
        """Create a DocumentValidator instance for testing."""
        return DocumentValidator(repo_root=temp_dir)

    @pytest.fixture
    def setup_shared_state(self, temp_dir):
        """Set up shared state directory with test documents."""
        shared_state_dir = temp_dir / ".iflow" / "skills" / ".shared-state"
        shared_state_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test documents
        (shared_state_dir / "test-document.md").write_text("# Test Document\n\nContent here.")
        (shared_state_dir / "another-test.md").write_text("# Another Test\n\nMore content.")
        (shared_state_dir / "empty.md").write_text("")
        
        return shared_state_dir

    def test_document_validator_initialization(self, temp_dir):
        """Test DocumentValidator initialization."""
        validator = DocumentValidator(repo_root=temp_dir)

        assert validator.repo_root == temp_dir
        assert validator.schema_dir == temp_dir / ".iflow" / "schemas"
        assert validator.shared_state_dir == temp_dir / ".iflow" / "skills" / ".shared-state"

    def test_document_validator_custom_schema_dir(self, temp_dir):
        """Test DocumentValidator with custom schema directory."""
        custom_schema_dir = temp_dir / "custom_schemas"
        validator = DocumentValidator(repo_root=temp_dir, schema_dir=custom_schema_dir)

        assert validator.schema_dir == custom_schema_dir

    def test_validate_required_documents_all_exist(self, document_validator, setup_shared_state):
        """Test validating when all required documents exist."""
        required_docs = ["test-document.md", "another-test.md"]

        code, message, results = document_validator.validate_required_documents(
            phase_name="test-phase",
            required_docs=required_docs
        )

        assert code == 0
        assert "All required documents validated" in message
        assert len(results) == 2
        assert all(result["exists"] for result in results)

    def test_validate_required_documents_missing_document(self, document_validator, setup_shared_state):
        """Test validating when a required document is missing."""
        required_docs = ["test-document.md", "nonexistent.md"]

        code, message, results = document_validator.validate_required_documents(
            phase_name="test-phase",
            required_docs=required_docs
        )

        assert code == 1
        assert "1 document(s) failed validation" in message
        assert len(results) == 2
        assert results[0]["exists"] is True
        assert results[1]["exists"] is False

    def test_validate_required_documents_empty_required_list(self, document_validator):
        """Test validating with empty required documents list."""
        code, message, results = document_validator.validate_required_documents(
            phase_name="test-phase",
            required_docs=[]
        )

        assert code == 0
        assert len(results) == 0

    def test_find_document(self, document_validator, setup_shared_state):
        """Test finding a document by name."""
        doc_path = document_validator._find_document("test-document.md")

        assert doc_path is not None
        assert doc_path.exists()
        assert doc_path.name == "test-document.md"

    def test_find_nonexistent_document(self, document_validator):
        """Test finding a nonexistent document."""
        doc_path = document_validator._find_document("nonexistent.md")

        assert doc_path is None

    def test_validate_document_content_valid(self, document_validator, setup_shared_state):
        """Test validating document content."""
        doc_path = setup_shared_state / "test-document.md"

        is_valid, issues = document_validator._validate_document_content(doc_path, "test-document.md")

        assert is_valid is True
        assert len(issues) == 0

    def test_validate_document_content_empty(self, document_validator, setup_shared_state):
        """Test validating empty document content."""
        doc_path = setup_shared_state / "empty.md"

        is_valid, issues = document_validator._validate_document_content(doc_path, "empty.md")

        assert is_valid is False
        assert len(issues) > 0

    def test_validate_document_structure(self, document_validator, temp_dir):
        """Test validating document structure."""
        # Create a test document with structure
        doc_dir = temp_dir / ".iflow" / "skills" / ".shared-state"
        doc_dir.mkdir(parents=True, exist_ok=True)
        doc_path = doc_dir / "structured.md"
        doc_path.write_text("""# Title

## Section 1

Content here.

## Section 2

More content.
""")

        is_valid, issues = document_validator._validate_document_structure(doc_path)

        assert is_valid is True

    def test_validate_document_structure_invalid(self, document_validator, temp_dir):
        """Test validating invalid document structure."""
        doc_dir = temp_dir / ".iflow" / "skills" / ".shared-state"
        doc_dir.mkdir(parents=True, exist_ok=True)
        doc_path = doc_dir / "invalid.md"
        doc_path.write_text("No heading here")

        is_valid, issues = document_validator._validate_document_structure(doc_path)

        assert is_valid is False

    def test_validate_document_markdown_format(self, document_validator, temp_dir):
        """Test validating markdown format."""
        doc_dir = temp_dir / ".iflow" / "skills" / ".shared-state"
        doc_dir.mkdir(parents=True, exist_ok=True)
        doc_path = doc_dir / "markdown.md"
        doc_path.write_text("# Title\n\n- Item 1\n- Item 2\n\n**Bold** text.")

        is_valid, issues = document_validator._validate_markdown_format(doc_path)

        assert is_valid is True

    def test_log_validation(self, document_validator, temp_dir):
        """Test logging validation results."""
        results = [
            {
                "document": "test.md",
                "phase": "test-phase",
                "exists": True,
                "valid": True,
                "message": "Document validated",
                "issues": []
            }
        ]

        document_validator._log_validation("test-phase", results)

        assert document_validator.validation_log.exists()

        with open(document_validator.validation_log, 'r') as f:
            log_data = json.load(f)

        assert "test-phase" in log_data
        assert len(log_data["test-phase"]) == 1

    def test_validate_all_phases(self, document_validator, setup_shared_state):
        """Test validating documents for all phases."""
        phases = {
            "phase1": ["test-document.md"],
            "phase2": ["another-test.md"]
        }

        results = document_validator.validate_all_phases(phases)

        assert "phase1" in results
        assert "phase2" in results
        assert results["phase1"]["valid"] is True
        assert results["phase2"]["valid"] is True

    def test_get_document_metadata(self, document_validator, setup_shared_state):
        """Test getting document metadata."""
        doc_path = setup_shared_state / "test-document.md"
        metadata = document_validator._get_document_metadata(doc_path)

        assert "size" in metadata
        assert "created" in metadata
        assert "modified" in metadata
        assert metadata["size"] > 0

    def test_validate_document_schema(self, document_validator, temp_dir):
        """Test validating document against schema."""
        # Create a schema
        schema_dir = temp_dir / ".iflow" / "schemas"
        schema_dir.mkdir(parents=True, exist_ok=True)
        schema_path = schema_dir / "test-schema.json"
        schema_path.write_text(json.dumps({
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["title", "content"]
        }))

        # Create a test document as JSON
        doc_dir = temp_dir / ".iflow" / "skills" / ".shared-state"
        doc_dir.mkdir(parents=True, exist_ok=True)
        doc_path = doc_dir / "test.json"
        doc_path.write_text(json.dumps({
            "title": "Test Title",
            "content": "Test Content"
        }))

        with patch.object(document_validator.schema_validator, 'validate_json_schema', return_value=(True, [])):
            is_valid, issues = document_validator._validate_document_schema(doc_path, "test-schema.json")

        assert is_valid is True

    def test_validate_document_schema_invalid(self, document_validator, temp_dir):
        """Test validating document against invalid schema."""
        # Create a schema
        schema_dir = temp_dir / ".iflow" / "schemas"
        schema_dir.mkdir(parents=True, exist_ok=True)
        schema_path = schema_dir / "test-schema.json"
        schema_path.write_text(json.dumps({
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["title", "content"]
        }))

        # Create a test document as JSON (missing required field)
        doc_dir = temp_dir / ".iflow" / "skills" / ".shared-state"
        doc_dir.mkdir(parents=True, exist_ok=True)
        doc_path = doc_dir / "test.json"
        doc_path.write_text(json.dumps({
            "title": "Test Title"
        }))

        with patch.object(document_validator.schema_validator, 'validate_json_schema', return_value=(False, ["Missing required field: content"])):
            is_valid, issues = document_validator._validate_document_schema(doc_path, "test-schema.json")

        assert is_valid is False
        assert len(issues) > 0

    def test_get_validation_summary(self, document_validator, setup_shared_state):
        """Test getting validation summary."""
        required_docs = ["test-document.md", "another-test.md"]
        code, message, results = document_validator.validate_required_documents(
            phase_name="test-phase",
            required_docs=required_docs
        )

        summary = document_validator.get_validation_summary(results)

        assert "total" in summary
        assert "valid" in summary
        assert "invalid" in summary
        assert summary["total"] == 2
        assert summary["valid"] == 2
        assert summary["invalid"] == 0

    def test_validate_document_encoding(self, document_validator, temp_dir):
        """Test validating document encoding."""
        doc_dir = temp_dir / ".iflow" / "skills" / ".shared-state"
        doc_dir.mkdir(parents=True, exist_ok=True)
        doc_path = doc_dir / "encoding.md"
        doc_path.write_text("# Test\n\nContent with UTF-8: é, ñ, 中文", encoding='utf-8')

        is_valid, issues = document_validator._validate_encoding(doc_path)

        assert is_valid is True

    def test_validate_document_encoding_invalid(self, document_validator, temp_dir):
        """Test validating document with invalid encoding."""
        doc_dir = temp_dir / ".iflow" / "skills" / ".shared-state"
        doc_dir.mkdir(parents=True, exist_ok=True)
        doc_path = doc_dir / "invalid-encoding.md"
        
        # Write with invalid UTF-8 sequence
        with open(doc_path, 'wb') as f:
            f.write(b'# Test\n\nInvalid UTF-8: \xff\xfe')

        is_valid, issues = document_validator._validate_encoding(doc_path)

        assert is_valid is False

    def test_check_document_completeness(self, document_validator, setup_shared_state):
        """Test checking document completeness."""
        doc_path = setup_shared_state / "test-document.md"
        required_sections = ["Title", "Content"]

        is_complete, missing = document_validator._check_completeness(doc_path, required_sections)

        # The test document has a title, so it should be complete
        assert is_complete is True or len(missing) < len(required_sections)

    def test_validate_document_links(self, document_validator, temp_dir):
        """Test validating document links."""
        doc_dir = temp_dir / ".iflow" / "skills" / ".shared-state"
        doc_dir.mkdir(parents=True, exist_ok=True)
        doc_path = doc_dir / "links.md"
        doc_path.write_text("""# Links

[Valid Link](#section)

[Invalid Link](nonexistent.md)
""")

        valid_links, invalid_links = document_validator._validate_links(doc_path)

        assert len(valid_links) > 0
        assert len(invalid_links) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])