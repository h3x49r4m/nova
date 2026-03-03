# Zsh completion script for iFlow CLI

#compdef i-flow

_i-flow() {
    local -a commands skills

    # Available commands
    commands=(
        'help:Show help information'
        'version:Show version information'
        'list:List available items'
        'invoke:Invoke a skill'
        'status:Show status information'
        'config:Manage configuration'
    )

    # Available skills
    skills=(
        'client:Client - Requirements provider and stakeholder'
        'devops-engineer:DevOps Engineer - CI/CD and infrastructure'
        'documentation-specialist:Documentation Specialist - Documentation creation'
        'git-flow:Git Flow - Gate-based workflow orchestration'
        'git-manage:Git Manage - Standardized git operations'
        'product-manager:Product Manager - Feature planning and prioritization'
        'project-manager:Project Manager - Sprint planning and resource allocation'
        'qa-engineer:QA Engineer - Quality validation and manual testing'
        'security-engineer:Security Engineer - Security validation and scanning'
        'software-engineer:Software Engineer - Full-stack implementation'
        'tech-lead:Tech Lead - Architecture design and technical strategy'
        'testing-engineer:Testing Engineer - Test automation and frameworks'
        'ui-ux-designer:UI/UX Designer - Design creation and user experience'
        'team-pipeline-auto-review:Team Pipeline - Auto Review'
        'team-pipeline-fix-bug:Team Pipeline - Fix Bug'
        'team-pipeline-new-feature:Team Pipeline - New Feature'
        'team-pipeline-new-project:Team Pipeline - New Project'
    )

    # Main command completion
    if (( CURRENT == 2 )); then
        _describe -t commands 'commands' commands
        _describe -t skills 'skills' skills
        return
    fi

    # Get the current command/skill
    local cmd="${words[2]}"

    case "${cmd}" in
        help|version)
            # No additional completion
            ;;
        invoke)
            # Complete skill names
            _describe -t skills 'skills' skills
            ;;
        list)
            _arguments \
                '--skills[List available skills]' \
                '--versions[List available versions]' \
                '--workflows[List available workflows]' \
                '--all[List everything]'
            ;;
        status)
            _describe -t skills 'skills' skills
            _arguments '--all[Show status for all skills]'
            ;;
        config)
            _arguments \
                '--get[Get configuration value]' \
                '--set[Set configuration value]' \
                '--list[List all configuration]' \
                '--edit[Edit configuration file]'
            ;;
        *)
            # Skill-specific options
            _arguments \
                '--help[Show help]' \
                '--version[Show version]' \
                '--config[Use custom config file]' \
                '--workflow[Specify workflow]' \
                '--dry-run[Run without making changes]' \
                '--verbose[Show verbose output]' \
                '--quiet[Suppress output]' \
                '--debug[Show debug information]'
            ;;
    esac
}

_i-flow "$@"