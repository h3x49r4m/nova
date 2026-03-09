#!/usr/bin/env python3
"""Test suite for transactional state manager.

Tests transaction-based state updates with ACID-like properties.
"""

import json
import tempfile
import unittest
from pathlib import Path

# Import transactional state manager
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.transactional_state import (
    TransactionalStateManager,
    StateTransaction,
    TransactionError,
    TransactionState
)


class TestStateTransaction(unittest.TestCase):
    """Test state transaction functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_dir = Path(self.temp_dir) / "state"
        self.state_dir.mkdir(parents=True)
        
        # Create a state file
        self.state_file = self.state_dir / "test-state.json"
        self.state_file.write_text(json.dumps({"key": "value"}))
        
        # Create transaction
        self.transaction = StateTransaction(
            transaction_id="test-tx",
            state_files=[self.state_file],
            temp_dir=self.state_dir / ".transactions" / "test-tx"
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_transaction_initialization(self):
        """Test transaction initialization."""
        self.assertEqual(self.transaction.transaction_id, "test-tx")
        self.assertEqual(self.transaction.state, TransactionState.ACTIVE)
        self.assertEqual(len(self.transaction.operations), 0)
        self.assertEqual(len(self.transaction.backup_files), 1)
        self.assertIn(self.state_file, self.transaction.backup_files)
    
    def test_add_operation(self):
        """Test adding operations to transaction."""
        self.transaction.add_operation(
            "update",
            self.state_file,
            {"key": "old"},
            {"key": "new"}
        )
        
        self.assertEqual(len(self.transaction.operations), 1)
        self.assertEqual(self.transaction.operations[0]["operation_type"], "update")
        self.assertEqual(self.transaction.operations[0]["old_data"], {"key": "old"})
        self.assertEqual(self.transaction.operations[0]["new_data"], {"key": "new"})
    
    def test_commit(self):
        """Test committing a transaction."""
        self.transaction.commit()
        
        self.assertEqual(self.transaction.state, TransactionState.COMMITTED)
        self.assertIsNotNone(self.transaction.completed_at)
        self.assertFalse(self.transaction.temp_dir.exists())
    
    def test_rollback(self):
        """Test rolling back a transaction."""
        # Modify state file
        self.state_file.write_text(json.dumps({"key": "modified"}))
        
        # Rollback
        self.transaction.rollback()
        
        # Verify file was restored
        data = json.loads(self.state_file.read_text())
        self.assertEqual(data, {"key": "value"})
        self.assertEqual(self.transaction.state, TransactionState.ROLLED_BACK)
        self.assertFalse(self.transaction.temp_dir.exists())
    
    def test_get_duration(self):
        """Test getting transaction duration."""
        duration = self.transaction.get_duration()
        self.assertEqual(duration, "Not completed")
        
        self.transaction.commit()
        duration = self.transaction.get_duration()
        self.assertNotEqual(duration, "Not completed")


class TestTransactionalStateManager(unittest.TestCase):
    """Test transactional state manager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_dir = Path(self.temp_dir) / "state"
        self.state_dir.mkdir(parents=True)
        
        self.manager = TransactionalStateManager(self.state_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_transaction_success(self):
        """Test successful transaction."""
        state_file = self.state_dir / "test-state.json"
        
        with self.manager.transaction([state_file]) as tx:
            self.manager.update_state(state_file, {"key": "new-value"})
        
        # Verify changes were committed
        data = self.manager.read_state(state_file)
        self.assertEqual(data, {"key": "new-value"})
        
        # Verify transaction was logged
        history = self.manager.get_transaction_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["state"], "committed")
    
    def test_transaction_rollback(self):
        """Test transaction rollback on failure."""
        state_file = self.state_dir / "test-state.json"
        state_file.write_text(json.dumps({"key": "original"}))
        
        from utils.exceptions import IFlowError
        
        try:
            with self.manager.transaction([state_file]) as tx:
                self.manager.update_state(state_file, {"key": "modified"})
                
                # Simulate failure
                raise ValueError("Simulated error")
        except IFlowError:
            pass
        
        # Verify rollback occurred
        data = self.manager.read_state(state_file)
        self.assertEqual(data, {"key": "original"})
    
    def test_multiple_files_transaction(self):
        """Test transaction with multiple files."""
        file1 = self.state_dir / "file1.json"
        file2 = self.state_dir / "file2.json"
        file3 = self.state_dir / "file3.json"
        
        with self.manager.transaction([file1, file2, file3]) as tx:
            self.manager.update_state(file1, {"file": 1})
            self.manager.update_state(file2, {"file": 2})
            self.manager.update_state(file3, {"file": 3})
        
        # Verify all files were updated
        self.assertEqual(self.manager.read_state(file1), {"file": 1})
        self.assertEqual(self.manager.read_state(file2), {"file": 2})
        self.assertEqual(self.manager.read_state(file3), {"file": 3})
    
    def test_delete_state_in_transaction(self):
        """Test deleting a state file within a transaction."""
        state_file = self.state_dir / "test-state.json"
        state_file.write_text(json.dumps({"key": "value"}))
        
        with self.manager.transaction([state_file]) as tx:
            self.manager.delete_state(state_file)
        
        # Verify file was deleted
        self.assertFalse(state_file.exists())
    
    def test_nested_transaction_prevention(self):
        """Test that nested transactions are prevented."""
        state_file = self.state_dir / "test-state.json"
        
        with self.manager.transaction([state_file]) as tx1:
            try:
                with self.manager.transaction([state_file]) as tx2:
                    self.fail("Nested transaction should not be allowed")
            except TransactionError as e:
                self.assertIn("Nested transactions", str(e))
    
    def test_transaction_without_context(self):
        """Test calling update_state outside transaction."""
        state_file = self.state_dir / "test-state.json"
        
        with self.assertRaises(TransactionError):
            self.manager.update_state(state_file, {"key": "value"})
    
    def test_read_state(self):
        """Test reading state."""
        state_file = self.state_dir / "test-state.json"
        state_file.write_text(json.dumps({"key": "value"}))
        
        data = self.manager.read_state(state_file)
        self.assertEqual(data, {"key": "value"})
        
        # Test reading non-existent file
        data = self.manager.read_state(self.state_dir / "nonexistent.json")
        self.assertIsNone(data)
    
    def test_get_current_transaction(self):
        """Test getting current transaction."""
        state_file = self.state_dir / "test-state.json"
        
        self.assertIsNone(self.manager.get_current_transaction())
        
        with self.manager.transaction([state_file]) as tx:
            current = self.manager.get_current_transaction()
            self.assertEqual(current, tx)
        
        self.assertIsNone(self.manager.get_current_transaction())
    
    def test_transaction_history(self):
        """Test transaction history."""
        state_file = self.state_dir / "test-state.json"
        
        # Perform multiple transactions
        for i in range(3):
            with self.manager.transaction([state_file]) as tx:
                self.manager.update_state(state_file, {"iteration": i})
        
        history = self.manager.get_transaction_history()
        self.assertEqual(len(history), 3)
        
        # Test limit
        history_limited = self.manager.get_transaction_history(limit=2)
        self.assertEqual(len(history_limited), 2)
    
    def test_validation_function(self):
        """Test validation function during state update."""
        from utils.exceptions import IFlowError
        
        state_file = self.state_dir / "test-state.json"
        
        def validate_data(data):
            return isinstance(data, dict) and "required_field" in data
        
        with self.assertRaises(IFlowError):
            with self.manager.transaction([state_file]) as tx:
                self.manager.update_state(
                    state_file,
                    {"missing_field": "value"},
                    validate=validate_data
                )
    
    def test_cleanup_old_transactions(self):
        """Test cleanup of old transaction directories."""
        # Create some transaction directories
        transactions_dir = self.state_dir / ".transactions"
        transactions_dir.mkdir(parents=True)
        
        old_tx = transactions_dir / "old-transaction"
        old_tx.mkdir()
        
        # Mock modification time to make it old
        import time
        old_time = time.time() - (10 * 86400)  # 10 days ago
        import os
        os.utime(old_tx, (old_time, old_time))
        
        cleaned = self.manager.cleanup_old_transactions(max_age_days=7)
        
        self.assertEqual(cleaned, 1)
        self.assertFalse(old_tx.exists())


if __name__ == '__main__':
    unittest.main()