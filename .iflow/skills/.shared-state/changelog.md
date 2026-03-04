# Changelog

**Owner:** Documentation Specialist
**Contributors:** All Engineers

## Migration Guide

### Upgrading from Previous Versions

This section provides guidance for upgrading to the latest version of iFlow CLI Skills.

#### Recent Changes Requiring Attention

**Test Suite Improvements**
- Fixed import error in `test_utils.py` that was blocking test execution
- Added 51 new tests for InputSanitizer and Exceptions modules
- Test count increased from 52 to 103 (98% increase)
- **Action Required:** Run `python3 -m pytest` to verify all tests pass after upgrade

**Dependencies**
- `requirements.txt` now includes actual dependencies (pytest, pytest-asyncio, pytest-cov)
- **Action Required:** Run `pip install -r requirements.txt` to ensure all dependencies are installed

**Config Validation**
- Added schema validation to git-flow.py and git-manage.py config loading
- Config files are now validated against `.iflow/schemas/git-flow-config.json` and `.iflow/schemas/skill-config.json`
- **Action Required:** Review and update any custom config files to match the schema. Invalid configs will fall back to defaults with a warning.

**Performance Monitoring**
- Integrated MetricsCollector into git operations
- Git command execution times and success rates are now tracked
- **Action Required:** Optional - use `get_git_metrics()` function to retrieve metrics statistics

**Constants Updates**
- Added new timeout constants to `utils/constants.py` (Timeouts enum)
- Added new size and limit constants (BackupPolicy enum)
- **Action Required:** Optional - Review and update any hardcoded values in custom code to use these constants

**Breaking Changes**
- None in this release

#### General Upgrade Steps

1. **Backup your workspace**
   ```bash
   cp -r .iflow .iflow.backup
   ```

2. **Update dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run tests**
   ```bash
   cd .iflow/skills
   python3 -m pytest tests/
   ```

4. **Validate configs**
   - Check git-flow config: `.iflow/skills/git-flow/config.json`
   - Check git-manage config: `.iflow/skills/git-manage/config.json`
   - Validation errors will be logged as warnings

5. **Test workflows**
   - Run a sample workflow to ensure compatibility
   - Check metrics: `python3 -c "from utils.git_command import get_git_metrics; print(get_git_metrics())"`

#### Rollback Procedure

If issues occur after upgrade:

1. Restore backup:
   ```bash
   rm -rf .iflow
   mv .iflow.backup .iflow
   ```

2. Reinstall previous dependencies

3. Verify functionality

---

## [Unreleased]

### Added
- Test import error fix in test_utils.py
- 51 new tests for InputSanitizer and Exceptions modules
- Config validation for git-flow and git-manage
- Performance metrics integration for git operations
- New timeout and size constants in utils/constants.py

### Changed
- Test coverage increased from 9.5% to 19.8%
- State file locations standardized to `.iflow/skills/.shared-state/`
- Secret detection enforced in all git operations (already active)
- Dependencies properly declared in requirements.txt

### Deprecated
*Features marked for deprecation.*

### Removed
*Removed features.*

### Fixed
- Critical import error blocking test execution
- Config validation warnings now properly logged

### Security
- Config validation prevents invalid configurations
- Secret detection verified as active in all git operations