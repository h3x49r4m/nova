# Shell Completion Scripts for iFlow CLI

This directory contains shell completion scripts for the iFlow CLI tool.

## Installation

### Bash

1. Copy the completion script to your system completion directory:
   ```bash
   sudo cp completion.bash /etc/bash_completion.d/i-flow
   ```

   Or copy to your home directory:
   ```bash
   cp completion.bash ~/.i-flow-completion.bash
   ```

2. Source the completion script in your `.bashrc`:
   ```bash
   echo 'source ~/.i-flow-completion.bash' >> ~/.bashrc
   source ~/.bashrc
   ```

### Zsh

1. Copy the completion script to your Zsh completion directory:
   ```bash
   cp completion.zsh ~/.zsh/completion/_i-flow
   ```

   Or to the system-wide completion directory:
   ```bash
   sudo cp completion.zsh /usr/share/zsh/vendor-completions/_i-flow
   ```

2. Add the completion directory to your `.zshrc`:
   ```bash
   echo 'fpath=(~/.zsh/completion $fpath)' >> ~/.zshrc
   autoload -U compinit && compinit
   ```

## Usage

Once installed, you can use tab completion for:

- Main commands: `help`, `version`, `list`, `invoke`, `status`, `config`
- All skills: `client`, `devops-engineer`, `git-flow`, `git-manage`, etc.
- Command options: `--help`, `--version`, `--verbose`, `--quiet`, etc.
- Skill-specific workflows and configurations

### Examples

```bash
# Complete commands
i-flow <TAB>

# Complete skills
i-flow invoke <TAB>

# Complete options
i-flow invoke git-flow --<TAB>
```

## Features

- Bash and Zsh support
- Command and skill completion
- Option and flag completion
- Context-aware suggestions
- Descriptions for commands and skills

## Updating

To update the completion scripts after adding new skills or commands:

1. Copy the new version of the completion script
2. Restart your shell or re-source the completion file

```bash
source ~/.bashrc  # For Bash
exec zsh         # For Zsh
```