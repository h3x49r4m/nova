---
name: git-manage
description: Provides standardized git operations for the evo project with safety checks and best practices
version: 2.0.0
category: development-process
---

# Git Management Skill

Provides standardized git operations for the evo project with safety checks and best practices.

## Usage

```
/git-manage <command> [options]
```

## Available Commands

### Status Check
```
/git-manage status
```
Shows git status with test results, coverage, and pending checks.

### Add Files
```
/git-manage add <files...>
```
Stage files for commit. Supports glob patterns.

### Commit
```
/git-manage commit <type>[:scope] <description>
```
Create a commit with conventional commit format.

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `refactor` - Code refactoring
- `test` - Adding/updating tests
- `docs` - Documentation
- `chore` - Maintenance tasks

**Options:**
- `--scope SCOPE` - Add scope to commit type
- `--body BODY` - Add detailed body with "Changes:" section
- `--no-verify` - Skip pre-commit checks

**Examples:**
```
/git-manage commit feat: implement memory system
/git-manage commit fix: correct safety constraint check
/git-manage commit test: add integration tests for decision engine
/git-manage commit feat auth: add JWT authentication --body "Implement secure authentication.

Changes:
- Add JWT token generation
- Implement password hashing
- Add auth middleware"
```

### Commit with Auto-Detection
```
/git-manage commit -a <description>
```
Auto-detects scope from changed files.

### Commit with No Verify
```
/git-manage commit --no-verify <type>[:scope] <description>
```
Skip pre-commit checks for trivial commits (e.g., typos, docs).

### Diff
```
/git-manage diff [staged|unstaged|<commit>]
```
Show changes. Default: unstaged changes. Use `staged` for staged changes.

### Undo Last Commit
```
/git-manage undo [soft|hard]
```
Undo the last commit. `soft` keeps changes (default), `hard` discards them.

### Amend Last Commit
```
/git-manage amend [description]
```
Modify the last commit. Add description to update commit message.

### Stash Operations
```
/git-manage stash save <message>    # Save changes
/git-manage stash pop               # Restore and remove stash
/git-manage stash list              # List stashes
/git-manage stash drop <index>      # Remove specific stash
```

### Log
```
/git-manage log [oneline|full|n=<count>]
```
Show commit history. Default: `oneline`. Use `full` for detailed view.

### Revert
```
/git-manage revert <commit>
```
Revert a specific commit, creating a new commit with opposite changes.

### Clean
```
/git-manage clean [dry-run|force]
```
Remove untracked files. `dry-run` shows what would be removed (default), `force` removes them.

### Changelog
```
/git-manage changelog [from=<tag>|<commit>] [to=<tag>|<commit>]
```
Generate changelog from commit messages between two points.

### Tag Operations
```
/git-manage tag create <name> [message]    # Create tag
/git-manage tag list                       # List tags
/git-manage tag delete <name>              # Delete tag
```

### Push
```
/git-manage push [remote] [branch]
```
Push commits with pre-push validation.

### Branch Operations
```
/git-manage branch create <name>        # Create new branch
/git-manage branch switch <name>        # Switch to branch
/git-manage branch delete <name>        # Delete branch
/git-manage branch list                 # List branches
```

## Pre-Commit Checks

Before any commit (unless `--no-verify` is used), the skill runs:

1. **Test Suite** - `pytest tests/ -v --cov` (or project-specific test command)
2. **TDD Enforcement** - Invokes `tdd-enforce` skill
3. **Coverage Verification** - Ensures coverage meets configured thresholds

**Blocking Rules:**
- Any test failure → Block commit
- Critical TDD violations → Block commit
- Coverage below configured threshold → Block commit

**Configurable Thresholds:**
Coverage thresholds can be configured in `config.json`:
```json
{
  "preCommit": {
    "testCommand": "pytest tests/ -v --cov",
    "coverageThreshold": {
      "lines": 90,
      "branches": 80
    },
    "runTddCheck": true
  }
}
```

If `config.json` is not found, defaults to:
- Coverage threshold: 90% lines, 80% branches
- TDD check: enabled

## Commit Standards

### Conventional Commit Format
```
<type>[optional scope]: <description>

[optional body]

[optional footer]
```

### Auto-Generated Message Template
```
<type>[<scope>]: <description>

[optional body with detailed description]

Changes:
- <description of change 1>
- <description of change 2>
- <description of change 3>
- ...

---
Branch: <branch name>

Files changed:
- <file1>
- <file2>
- ...

Verification:
- Tests: passed/skipped/N/A
- Coverage: <percentage>%/N/A
- Architecture: ✓ compliant (only shown when architecture check runs)
- TDD: ✓ compliant (only shown when TDD check runs)
```

**Note:** The "Changes:" section with bullet points should be included in the body parameter when committing, describing the specific changes made in detail. The "Files changed:" section is automatically generated from the staged files. The Verification section shows test results, coverage (when checked), and Architecture/TDD compliance (only when those checks are actually run).

**Note:** The "Changes:" section with bullet points should be included in the body parameter when committing, describing the specific changes made in detail. The "Files changed:" section is automatically generated from the staged files.

## Safety Mechanisms

### Secrets Detection
Scans for common secret patterns before committing:
- API keys (`api_key`, `apikey`, `secret`)
- Tokens (`token`, `access_token`)
- Passwords (`password`, `passwd`)
- Private keys (`private_key`, `.pem`)

### Branch Protection
- Prevents direct commits to `main` without review
- Requires feature branch workflow for major changes
- Validates branch naming conventions (`feat/`, `fix/`, `refactor/`)

### Backup Before Destructive Ops
Before `reset --hard` or `clean -fd`:
- Creates backup stash
- Shows confirmation prompt
- Allows rollback

## Integration with Existing Skills

### TDD Enforcement
- Automatically invoked before each commit
- Blocks commits if TDD cycle incomplete
- Report included in commit message

## Exit Codes

- `0` - Success
- `1` - Tests failed
- `2` - TDD violations detected
- `3` - No changes to commit
- `4` - Secrets detected
- `5` - Coverage below threshold
- `6` - Branch protection violation
- `7` - No stash to pop
- `8` - Invalid commit hash
- `9` - Tag not found

## Examples

### View Changes Before Committing
```bash
# Show unstaged changes
/git-manage diff

# Show staged changes
/git-manage diff staged

# Show specific commit changes
/git-manage diff abc1234
```

### Undo and Amend
```bash
# Undo last commit (keep changes)
/git-manage undo soft

# Add forgotten file and amend
/git-manage add forgotten_file.py
/git-manage amend "add missing file"
```

### Stash Workflow
```bash
# Save work in progress
/git-manage stash save "WIP: feature x"

# Switch branches and work
/git-manage branch switch feat/y

# Return and restore work
/git-manage branch switch feat/x
/git-manage stash pop
```

### View History
```bash
# Quick history
/git-manage log

# Detailed history
/git-manage log full

# Last 10 commits
/git-manage log n=10
```

### Complete Workflow
```bash
# Check status with test results
/git-manage status

# Stage new implementation files
/git-manage add evo/src/evo/memory/
/git-manage add tests/test_memory_system.py

# Commit with auto-detection
/git-manage commit -a "implement three-tier memory system"

# Push to remote
/git-manage push origin feat/memory-system
```

### Commit with Detailed Changes
```bash
# Stage files
/git-manage add file1.py file2.py

# Commit with body containing detailed changes
/git-manage commit feat "add user authentication" --body "Implement secure user authentication with JWT tokens and password hashing.

Changes:
- Add JWT token generation and validation
- Implement bcrypt password hashing
- Add authentication middleware
- Update user model with auth fields
- Add login and logout endpoints
- Implement refresh token rotation"
```

### Feature Branch Workflow
```bash
# Create feature branch
/git-manage branch create feat/capability-registry

# Work and commit changes
/git-manage add evo/src/evo/capability/
/git-manage commit feat: add dynamic capability tracking

# Push and merge
/git-manage push origin feat/capability-registry
```

## Custom Commit Hooks

The git-manage skill supports custom pre-commit hooks via configuration:

```json
{
  "preCommit": {
    "hooks": [
      {
        "name": "lint",
        "command": "npm run lint",
        "blocking": true
      },
      {
        "name": "type-check",
        "command": "npm run type-check",
        "blocking": true
      },
      {
        "name": "format-check",
        "command": "npm run format:check",
        "blocking": false
      }
    ]
  }
}
```

**Hook Configuration:**
- `name`: Hook identifier for logging
- `command`: Shell command to execute
- `blocking`: If `true`, commit is blocked on failure; if `false`, only warnings shown

Hooks are executed in order after test suite and before final commit.

## Implementation Notes

This skill uses:
- `git` command for all git operations
- `pytest` or project-specific test command for test execution
- `tdd-enforce` skill for TDD compliance verification
- Pattern matching for secrets detection
- Conventional commits parser for message validation
- `config.json` for customizable thresholds and hooks

## Error Handling

### Common Errors
- **Pre-Commit Check Failures**: Tests fail, TDD violations, or coverage below threshold
- **Secret Detection**: Secrets detected in staged files
- **Branch Protection**: Attempting to commit to protected branch
- **Merge Conflicts**: Conflicts during merge or rebase operations
- **Invalid Commit Hash**: Specified commit hash doesn't exist

### Rollback Scenarios
- **Commit Reversal**: Use `undo` command to revert last commit (soft or hard)
- **Stash Recovery**: Use `stash pop` or `stash list` to recover stashed changes
- **Branch Recovery**: Use `git reflog` to recover deleted branches
- **Reset Recovery**: Use backup stash created before destructive operations

### Recovery Procedures
1. **Check Git Status**: Verify current state with `git status`
2. **Review Changes**: Use `git diff` to review staged and unstaged changes
3. **Use Stash**: Stash changes before destructive operations
4. **Backup Before Reset**: Always create backup stash before `reset --hard`
5. **Verify Commit Hash**: Use `git log` to verify commit hash before operations
6. **Test Locally**: Run tests and checks before pushing changes
