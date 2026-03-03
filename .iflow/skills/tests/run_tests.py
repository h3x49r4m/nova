#!/usr/bin/env python3
"""
Test runner for all iFlow CLI skills tests.
Provides convenient command-line interface for running tests.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_skill_manager import (
    TestSkillVersionManager,
    TestSkillRegistry,
    TestSkillDependencyResolver,
    TestSkillCompatibilityChecker
)
from test_git_flow import (
    TestBranchStatus,
    TestPhaseStatus,
    TestWorkflowStatus,
    TestReviewEvent,
    TestBranchState,
    TestPhase,
    TestWorkflowState,
    TestDependencyGraph,
    TestGitFlow,
    TestGitFlowAdvanced
)
from test_git_manage import (
    TestGitManage,
    TestGitManageConfig,
    TestGitManageConstants
)
from test_utils import (
    TestGitCommand,
    TestSchemaValidator,
    TestFileLock,
    TestConstants,
    TestIntegration
)


def run_tests(verbosity=2):
    """Run all tests with specified verbosity."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add skill manager tests
    suite.addTests(loader.loadTestsFromTestCase(TestSkillVersionManager))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillRegistry))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillDependencyResolver))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillCompatibilityChecker))
    
    # Add git-flow tests
    suite.addTests(loader.loadTestsFromTestCase(TestBranchStatus))
    suite.addTests(loader.loadTestsFromTestCase(TestPhaseStatus))
    suite.addTests(loader.loadTestsFromTestCase(TestWorkflowStatus))
    suite.addTests(loader.loadTestsFromTestCase(TestReviewEvent))
    suite.addTests(loader.loadTestsFromTestCase(TestBranchState))
    suite.addTests(loader.loadTestsFromTestCase(TestPhase))
    suite.addTests(loader.loadTestsFromTestCase(TestWorkflowState))
    suite.addTests(loader.loadTestsFromTestCase(TestDependencyGraph))
    suite.addTests(loader.loadTestsFromTestCase(TestGitFlow))
    suite.addTests(loader.loadTestsFromTestCase(TestGitFlowAdvanced))
    
    # Add git-manage tests
    suite.addTests(loader.loadTestsFromTestCase(TestGitManage))
    suite.addTests(loader.loadTestsFromTestCase(TestGitManageConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestGitManageConstants))
    
    # Add utility tests
    suite.addTests(loader.loadTestsFromTestCase(TestGitCommand))
    suite.addTests(loader.loadTestsFromTestCase(TestSchemaValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestFileLock))
    suite.addTests(loader.loadTestsFromTestCase(TestConstants))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run skill manager tests')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Increase output verbosity')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Decrease output verbosity')
    
    args = parser.parse_args()
    
    verbosity = 2
    if args.verbose:
        verbosity = 3
    elif args.quiet:
        verbosity = 1
    
    return run_tests(verbosity)


if __name__ == '__main__':
    sys.exit(main())