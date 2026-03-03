# Nova

A comprehensive skills-based development system for the iFlow CLI, featuring 12 role-based skills, 3 pipeline orchestrators, and advanced git workflow automation.

## Overview

iFlow CLI Skills transforms software development into a collaborative, role-based workflow where specialized AI agents work together through orchestrated pipelines. The system uses a shared state directory for seamless collaboration, supports version management, and includes gate-based workflow orchestration with reversible approvals.

## Features

### 🎭 Role-Based Skills
12 specialized development roles, each with specific responsibilities and state contracts:
- **Client** - Requirements provider and stakeholder
- **Product Manager** - Feature planning and prioritization
- **Project Manager** - Sprint planning and resource allocation
- **UI/UX Designer** - Design creation and user experience
- **Tech Lead** - Architecture design and technical strategy
- **Software Engineer** - Full-stack implementation
- **Testing Engineer** - Test automation and frameworks
- **QA Engineer** - Quality validation and manual testing
- **DevOps Engineer** - CI/CD and infrastructure
- **Security Engineer** - Security validation and scanning
- **Documentation Specialist** - Documentation creation

### 🚀 Pipeline Orchestrators
3 automated pipelines that coordinate multiple roles:
- **New Project Pipeline** - Complete development lifecycle from scratch
- **New Feature Pipeline** - Streamlined feature development for existing projects
- **Bug Fix Pipeline** - Rapid bug fixing workflow

### 🔄 Git Workflow Automation
- **git-flow** - Gate-based workflow orchestration with role-based branching, review/approval gates, phase tracking, and reversible approvals
- **git-manage** - Standardized git operations with safety checks, TDD enforcement, and conventional commits

### 📦 Version Management
Comprehensive version management infrastructure with:
- Semantic versioning for all skills
- Capability declarations per version
- Breaking change tracking
- Dependency resolution
- Compatibility checking between skills and pipelines

### 📊 Shared State System
Centralized state directory with 14 state documents:
- `project-spec.md` - Project requirements and features
- `design-spec.md` - UI/UX designs and prototypes
- `architecture-spec.md` - System architecture and tech stack
- `implementation-plan.md` - Task breakdown and timeline
- `implementation.md` - Full-stack implementation details
- `test-plan.md` - Test strategy and test cases
- `test-results.md` - Test execution results
- `quality-report.md` - Quality validation and bug reports
- `security-report.md` - Security analysis and vulnerabilities
- `deployment-status.md` - Deployment history and environment status
- `api-docs.md` - API documentation and schemas
- `user-guide.md` - User documentation and tutorials
- `changelog.md` - Change history and version notes
- `pipeline-status.md` - Pipeline progress and stage status

## Installation

### Prerequisites
- Python 3.14+
- iFlow CLI installed and configured
- Git installed and configured

### Setup

1. Clone the repository:
```bash
git clone git@github.com:h3x49r4m/nova.git
cd nova
```

2. Verify skill structure:
```bash
ls .iflow/skills/
```

3. Check skill status:
```bash
i-flow list --skills
```

## Usage

### Activating Skills

#### Single Role Activation
Activate a specific role to work independently:

```bash
# Activate as Client
i-flow invoke client

# Activate as Tech Lead
i-flow invoke tech-lead

# Activate as Software Engineer
i-flow invoke software-engineer
```

**Workflow:**
1. Role reads `.shared-state/` directory
2. Understands context and previous work
3. Performs its specialized tasks
4. Updates specific documents in `.shared-state/`
5. Updates `pipeline-status.md` with completion status

#### Pipeline Execution
Activate a pipeline to orchestrate multiple roles:

```bash
# New project pipeline (full development lifecycle)
i-flow invoke team-pipeline-new-project

# New feature pipeline (add features to existing project)
i-flow invoke team-pipeline-new-feature

# Bug fix pipeline (rapid bug fixing)
i-flow invoke team-pipeline-fix-bug
```

**Workflow:**
1. Orchestrator reads `config.json` for role sequence
2. Executes roles in defined sequence
3. Each role reads state, performs work, updates state
4. Orchestrator tracks progress via `pipeline-status.md`
5. Pipeline completes when all roles finish

### Git Workflow

#### Git-Flow Workflow

**Start a new feature workflow:**
```bash
i-flow invoke git-flow start "User Authentication"
```

**Commit changes:**
```bash
i-flow invoke git-flow commit src/auth.py
```

**Review pending branches:**
```bash
i-flow invoke git-flow review
```

**Approve a branch:**
```bash
i-flow invoke git-flow approve tech-lead/auth-architecture
```

**Reject a branch:**
```bash
i-flow invoke git-flow reject software-engineer/auth-api --reason "Tests failing"
```

**View workflow status:**
```bash
i-flow invoke git-flow status
```

**Advance to next phase:**
```bash
i-flow invoke git-flow phase-next
```

#### Git-Manage Workflow

**Check status with test results:**
```bash
i-flow invoke git-manage status
```

**Stage and commit changes:**
```bash
i-flow invoke git-manage add src/auth.py
i-flow invoke git-manage commit src/auth.py --type feat --description "implement user authentication"
```

**View changes:**
```bash
i-flow invoke git-manage diff
```

**Undo last commit:**
```bash
i-flow invoke git-manage undo soft
```

**Push to remote:**
```bash
i-flow invoke git-manage push origin feat/authentication
```

### Version Management

**List all skills:**
```bash
i-flow list --skills
```

**Check skill version:**
```bash
i-flow status software-engineer
```

**Check compatibility:**
```bash
i-flow list --versions
```

## Architecture

### Directory Structure

```
.iflow/
├── skills/                          # All skills (roles + pipelines)
│   ├── client/                      # Role skill
│   ├── product-manager/             # Role skill
│   ├── project-manager/             # Role skill
│   ├── ui-ux-designer/              # Role skill
│   ├── tech-lead/                   # Role skill
│   ├── software-engineer/           # Role skill
│   ├── testing-engineer/            # Role skill
│   ├── qa-engineer/                 # Role skill
│   ├── devops-engineer/             # Role skill
│   ├── security-engineer/           # Role skill
│   ├── documentation-specialist/    # Role skill
│   ├── git-flow/                    # Git workflow orchestrator
│   ├── git-manage/                  # Git operations skill
│   ├── team-pipeline-new-project/   # Pipeline orchestrator
│   ├── team-pipeline-new-feature/   # Pipeline orchestrator
│   └── team-pipeline-fix-bug/       # Pipeline orchestrator
│
└── .shared-state/                   # Shared state directory
    ├── project-spec.md
    ├── design-spec.md
    ├── architecture-spec.md
    ├── implementation-plan.md
    ├── implementation.md
    ├── test-plan.md
    ├── test-results.md
    ├── quality-report.md
    ├── security-report.md
    ├── deployment-status.md
    ├── api-docs.md
    ├── user-guide.md
    ├── changelog.md
    ├── pipeline-status.md
    └── templates/                   # Document templates
```

### Role Skill Structure

```
.iflow/skills/{role}/
├── SKILL.md                          # Role definition + state contracts
├── config.json                       # Role configuration
├── versions/                         # Version management
│   └── {version}/
│       ├── capabilities.json         # Capability declarations
│       ├── breaking_changes.json     # Breaking changes tracking
│       └── migrations/               # Migration scripts
└── workflows/                        # Role workflows
    └── {workflow-name}.md
```

### Pipeline Orchestrator Structure

```
.iflow/skills/{pipeline}/
├── SKILL.md                          # Pipeline definition
├── config.json                       # Pipeline configuration (role sequence)
└── versions/                         # Version management
    └── {version}/
        ├── capabilities.json
        ├── breaking_changes.json
        └── migrations/
```

## Workflows

### New Project Workflow

```
Client → Product Manager → Project Manager → UI/UX Designer → Tech Lead → 
Software Engineer → Testing Engineer → QA Engineer → DevOps Engineer → 
Security Engineer → Documentation Specialist
```

**Duration:** Complete development lifecycle

### New Feature Workflow

```
Client (optional) → Product Manager → Project Manager → UI/UX Designer → 
Tech Lead → Software Engineer → Testing Engineer → QA Engineer → 
DevOps Engineer (if needed) → Security Engineer → Documentation Specialist
```

**Duration:** Feature development cycle

### Bug Fix Workflow

```
Client (optional) → Tech Lead → Software Engineer → Testing Engineer → 
QA Engineer → DevOps Engineer (if critical hotfix) → Documentation Specialist (if needed)
```

**Duration:** Rapid bug fix cycle

## State-First Approach

Every role follows this pattern:

1. **READ STATE** - Read relevant documents from `.shared-state/`
2. **ANALYZE CONTEXT** - Understand previous work, requirements, constraints
3. **PERFORM WORK** - Execute role-specific tasks
4. **UPDATE STATE** - Write updated documents to `.shared-state/`
5. **REPORT STATUS** - Update `pipeline-status.md`

### State Contracts

Each role's `SKILL.md` defines:
- **READ contracts** - What documents to read before starting
- **WRITE contracts** - What documents to update after completing
- **Validation rules** - Rules for state consistency

## Configuration

### Skill Configuration

Each skill can be configured via `config.json`:

```json
{
  "version": "1.0.0",
  "capabilities": ["capability1", "capability2"],
  "compatible_pipelines": ["*"],
  "dependencies": {}
}
```

### Git-Flow Configuration

Edit `.iflow/skills/git-flow/config.json`:

```json
{
  "workflow": {
    "auto_detect_role": true,
    "auto_create_branch": true,
    "auto_phase_transition": true,
    "require_all_phases": false,
    "allow_parallel_phases": false
  },
  "merge": {
    "strategy": "rebase-merge",
    "delete_branch_after_merge": true,
    "require_dependencies_merged": true
  },
  "unapproval": {
    "allow_unapprove_after_merge": true,
    "default_action": "cascade-revert",
    "require_cascade_confirmation": true
  }
}
```

### Git-Manage Configuration

Edit `.iflow/skills/git-manage/config.json`:

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

## Testing



Run the test suite:



```bash

i-flow invoke testing-engineer --run-all

```



Or run directly:



```bash

python3 -m pytest .iflow/skills/tests/ -v

```



Run specific tests:



```bash

# Git-flow tests

python3 -m pytest .iflow/skills/tests/test_git_flow.py -v



# Git-manage tests

python3 -m pytest .iflow/skills/tests/test_git_manage.py -v



# Utility tests

python3 -m pytest .iflow/skills/tests/test_utils.py -v

```



### Test Coverage



The project includes comprehensive test coverage for:

- Git workflow operations (git-flow, git-manage)

- Utility modules (logging, caching, validation, etc.)

- Version management and compatibility checking

- Error handling and recovery strategies



### CI/CD Integration



Automated testing is integrated into the development workflow via:

- Pre-commit test validation

- Coverage thresholds (configurable)

- Quality gates for merges

- Automated review pipelines

## Documentation

- [Design Document](docs/iflow_skills_design.md) - Architecture and design specifications
- [Roles](docs/roles.md) - Role definitions and responsibilities
- [Skills](docs/skills.md) - Skill capabilities and requirements
- [Team Flow](docs/team_flow.md) - Visual workflow diagram

## Benefits

1. **Single Source of Truth** - All state in one directory
2. **Independent Roles** - Roles can work alone or in pipelines
3. **State Persistence** - State survives across sessions
4. **Easy Resumption** - Resume from any stage
5. **Clear Ownership** - Each document has an owner
6. **Traceability** - Full audit trail via state documents
7. **Flexibility** - Mix single-role and pipeline workflows
8. **Consistency** - State contracts ensure consistency
9. **Scalability** - Easy to add new roles or pipelines
10. **Collaboration** - Shared state enables cross-role communication

## Contributing

1. Follow the existing code structure and conventions
2. Add appropriate tests for new features
3. Update documentation for any API changes
4. Ensure all tests pass before submitting

## License

See [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or contributions, please refer to the project repository.
