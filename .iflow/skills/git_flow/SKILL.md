---
name: git-flow
description: Gate-based workflow orchestration with role-based branching, review/approval gates, phase tracking, and reversible approvals
version: 1.0.0
category: development-process
---

# Git-Flow Skill

Provides gate-based workflow orchestration for feature development with role-based branching, review/approval gates, phase tracking, and reversible approvals. Delegates low-level git operations to git-manage.

## Usage

```
/git-flow <command> [options]
```

## Available Commands

### Start Workflow
```
/git-flow start <feature-name>
```
Initialize a new feature workflow with phase tracking.

**Example:**
```
/git-flow start "User Authentication"
```

### Commit Changes
```
/git-flow commit [files...]
```
Commit changes to the current role-based feature branch. Automatically creates branch if on protected branch.

**Example:**
```
/git-flow commit src/auth.py
/git-flow commit
```

### Review Dashboard
```
/git-flow review
```
Show all pending branches awaiting review with details about role, commits, and status.

### Approve Branch
```
/git-flow approve <branch> [--comment "text"]
```
Approve a branch and merge it to main using rebase-merge strategy.

**Example:**
```
/git-flow approve tech-lead/auth-architecture
/git-flow approve software-engineer/auth-api --comment "Great implementation!"
```

### Reject Branch
```
/git-flow reject <branch> --reason "text" [--keep-branch]
```
Reject a branch with a reason. Branch can be kept for fixes or deleted.

**Example:**
```
/git-flow reject tech-lead/memory-system --reason "Missing error handling"
/git-flow reject software-engineer/auth-api --reason "Tests failing" --keep-branch
```

### Request Changes
```
/git-flow request-changes <branch> --comment "text"
```
Request modifications on a branch without rejecting it.

**Example:**
```
/git-flow request-changes ui-ux-designer/login-page --comment "Make buttons larger"
```

### Unapprove Branch
```
/git-flow unapprove <branch> [--cascade]
```
Unapprove a previously merged branch. Use --cascade to revert all dependent branches.

**Example:**
```
/git-flow unapprove tech-lead/memory-system
/git-flow unapprove tech-lead/memory-system --cascade
```

### Workflow Status
```
/git-flow status
```
Show current workflow status, phase progress, and pending reviews.

### Advance Phase
```
/git-flow phase-next
```
Advance to the next phase after current phase is complete.

### Review History
```
/git-flow history
```
Show full review history with all approval/rejection events.

## Workflow Phases

The default workflow includes these phases:

1. **Requirements Gathering** (Client) - Required
2. **Architecture Design** (Tech Lead) - Required
3. **Implementation** (Software Engineer) - Required
4. **Testing** (QA Engineer) - Required
5. **Design** (UI/UX Designer) - Optional
6. **Documentation** (Documentation Specialist) - Optional
7. **Security Review** (Security Engineer) - Optional
8. **Deployment** (DevOps Engineer) - Required

## Role-Based Branching

Branches are automatically named using the convention:
```
{role-slug}/{feature-slug}-{short-id}
```

**Examples:**
- `tech-lead/memory-system-143022`
- `software-engineer/user-auth-143145`
- `qa-engineer/auth-tests-143210`

## State Machine

### Branch Status
```
pending → reviewing → approved → merged
                                    ↓
                               unapproved
                                    ↓
                               reverted → pending
needs_changes → pending
rejected → pending
```

### Phase Status
```
pending → active → complete
           ↓
        blocked
```

## Configuration

### Config Options

Edit `.iflow/skills/git-flow/config.json`:

```json
{
  "workflow": {
    "auto_detect_role": true,
    "auto_create_branch": true,
    "auto_phase_transition": true,
    "require_all_phases": false,
    "allow_parallel_phases": false,
    "phases_file": null
  },
  "merge": {
    "strategy": "rebase-merge",
    "delete_branch_after_merge": true,
    "require_dependencies_merged": true
  },
  "unapproval": {
    "allow_unapprove_after_merge": true,
    "default_action": "cascade-revert",
    "require_cascade_confirmation": true,
    "preserve_branch_after_revert": true,
    "auto_create_fix_branch": false
  },
  "git_manage": {
    "command_path": ".iflow/skills/git-manage/git-manage.py"
  },
  "branch_protection": {
    "protected_branches": ["main", "master", "production"]
  }
}
```

### Custom Phases

Create a custom phases file (e.g., `custom-phases.json`):

```json
{
  "phases": [
    {
      "name": "Custom Phase 1",
      "role": "Custom Role",
      "order": 1,
      "required": true
    }
  ]
}
```

Then update config.json:
```json
{
  "workflow": {
    "phases_file": "custom-phases.json"
  }
}
```

## Complete Workflow Example

```
# Initialize workflow
/git-flow start "User Authentication"

# Phase 1: Requirements Gathering (Client)
Client: /git-flow commit requirements.md
You: /git-flow review approve client/requirements-abc123

# Phase 2: Architecture Design (Tech Lead)
Tech Lead: /git-flow commit architecture.md
You: /git-flow review approve tech-lead/architecture-def456

# Phase 3: Implementation (Software Engineer)
Software Engineer: /git-flow commit src/auth.py
You: /git-flow review approve software-engineer/implementation-ghi789

# Later, bug found in Phase 2
You: /git-flow unapprove tech-lead/architecture-def456 --cascade

# Tech Lead fixes issues
Tech Lead: /git-flow commit architecture.md

# Resume workflow
You: /git-flow review approve tech-lead/architecture-fix-jkl012
You: /git-flow review approve software-engineer/implementation-ghi789

# Continue through remaining phases...
```

## Integration with git-manage

git-flow delegates low-level git operations to git-manage:

- **Commit creation**: Uses `git-manage commit`
- **Branch operations**: Uses `git-manage branch create/switch`
- **Diff viewing**: Uses `git-manage diff`

## State Persistence

Workflow state is persisted in:
- `.iflow/skills/git-flow/workflow-state.json` - Main workflow state
- `.iflow/skills/git-flow/branch-states.json` - Individual branch states

## Exit Codes

- `0` - Success
- `1` - Error (see error message for details)

## Notes

- Auto-branch creation is enabled by default for protected branches (main, master)
- Phase transitions can be automatic or manual based on configuration
- Unapproval with cascade reverts all dependent branches in reverse merge order
- All review events are logged for full audit trail

## Error Handling

### Common Errors
- **Branch Already Exists**: If branch already exists, switch to existing branch or use force option
- **Merge Conflicts**: Resolve conflicts manually or use automated conflict resolution tools
- **Protected Branch Violation**: Cannot commit directly to protected branches, use feature branches
- **Missing Workflow State**: If workflow state is corrupted, restore from backup or reinitialize

### Rollback Scenarios
- **Merge Errors**: If merge fails, abort merge, fix conflicts, and retry
- **Unapproval Failures**: If unapproval fails, manually revert commits and update state
- **Phase Transition Errors**: If phase transition fails, manually update phase and retry
- **State Corruption**: If workflow state is corrupted, restore from git history or backup

### Recovery Procedures
1. **Check Git Status**: Verify current git state and resolve any issues
2. **Backup Current State**: Create backup of workflow state before making changes
3. **Use Git Reflog**: Use `git reflog` to recover lost commits if needed
4. **Restore from Backup**: Restore workflow state from backup if corrupted
5. **Reinitialize Workflow**: If state is unrecoverable, reinitialize workflow from scratch