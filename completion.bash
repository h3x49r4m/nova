# Bash completion script for iFlow CLI

_i-flow_completion() {
    local cur prev words cword
    _init_completion || return

    # Available skills
    local skills="client devops-engineer documentation-specialist git-flow git-manage product-manager project-manager qa-engineer security-engineer software-engineer team-pipeline-auto-review team-pipeline-fix-bug team-pipeline-new-feature team-pipeline-new-project tech-lead testing-engineer ui-ux-designer"

    # Available commands
    local commands="help version list invoke status config"

    case "${prev}" in
        i-flow|--help|--version)
            return
            ;;
        invoke)
            COMPREPLY=($(compgen -W "${skills}" -- "${cur}"))
            return
            ;;
        list)
            COMPREPLY=($(compgen -W "--skills --versions --workflows --all" -- "${cur}"))
            return
            ;;
        status)
            COMPREPLY=($(compgen -W "${skills} --all" -- "${cur}"))
            return
            ;;
        config)
            COMPREPLY=($(compgen -W "--get --set --list --edit" -- "${cur}"))
            return
            ;;
        client|devops-engineer|documentation-specialist|git-flow|git-manage|product-manager|project-manager|qa-engineer|security-engineer|software-engineer|tech-lead|testing-engineer|ui-ux-designer|team-pipeline-auto-review|team-pipeline-fix-bug|team-pipeline-new-feature|team-pipeline-new-project)
            # Complete skill-specific options
            COMPREPLY=($(compgen -W "--help --version --config --workflow --dry-run --verbose --quiet" -- "${cur}"))
            return
            ;;
        *)
            ;;
    esac

    # Handle main command completion
    if [[ ${cword} -eq 1 ]]; then
        COMPREPLY=($(compgen -W "${commands} ${skills}" -- "${cur}"))
    else
        # Handle global options
        COMPREPLY=($(compgen -W "--help --version --verbose --quiet --debug --config" -- "${cur}"))
    fi
}

complete -F _i-flow_completion i-flow