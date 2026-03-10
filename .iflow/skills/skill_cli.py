#!/usr/bin/env python3
"""
Skill Management CLI
Command-line interface for managing skills, versions, and compatibility.
"""

import argparse
import json
from pathlib import Path
from typing import Optional

# Import skill manager classes
from skill_manager import (
    SkillRegistry,
    SkillDependencyResolver,
    SkillCompatibilityChecker
)


class SkillCLI:
    """CLI for skill management."""
    
    def __init__(self, skills_dir: Optional[Path] = None):
        if skills_dir is None:
            # Default to .iflow/skills directory
            self.skills_dir = Path.cwd() / '.iflow' / 'skills'
        else:
            self.skills_dir = skills_dir
        
        self.registry = SkillRegistry(self.skills_dir)
        self.resolver = SkillDependencyResolver(self.registry)
        self.checker = SkillCompatibilityChecker(self.registry)
    
    def list_skills(self, show_details: bool = False) -> int:
        """List all available skills."""
        skills = self.registry.list_skills()
        
        if not skills:
            print("No skills found.")
            return 0
        
        print(f"Available Skills ({len(skills)}):")
        print()
        
        for skill_name in skills:
            skill = self.registry.get_skill(skill_name)
            if skill:
                print(f"  {skill_name}")
                print(f"    Version: {skill.current_version}")
                print(f"    Available versions: {', '.join(skill.available_versions)}")
                
                if show_details:
                    caps = skill.get_capabilities(skill.current_version)
                    if caps:
                        capabilities = caps.get('capabilities', [])
                        print(f"    Capabilities: {', '.join(capabilities[:5])}")
                        if len(capabilities) > 5:
                            print(f"      ... and {len(capabilities) - 5} more")
                print()
        
        return 0
    
    def skill_info(self, skill_name: str) -> int:
        """Show detailed information about a skill."""
        skill = self.registry.get_skill(skill_name)
        
        if not skill:
            print(f"Skill '{skill_name}' not found.")
            return 1
        
        print(f"Skill: {skill_name}")
        print(f"Current Version: {skill.current_version}")
        print(f"Available Versions: {', '.join(skill.available_versions)}")
        print()
        
        # Show capabilities for current version
        caps = skill.get_capabilities(skill.current_version)
        if caps:
            print("Capabilities:")
            capabilities = caps.get('capabilities', [])
            for cap in capabilities:
                print(f"  - {cap}")
            print()
            
            # Show domain support
            domains = caps.get('domains', {})
            print("Domain Support:")
            for domain, info in domains.items():
                status = "✓" if info.get('supported', False) else "✗"
                print(f"  {status} {domain}")
                if not info.get('supported', False):
                    reason = info.get('reason', '')
                    if reason:
                        print(f"      Reason: {reason}")
            print()
        
        return 0
    
    def skill_versions(self, skill_name: str) -> int:
        """List all versions of a skill."""
        skill = self.registry.get_skill(skill_name)
        
        if not skill:
            print(f"Skill '{skill_name}' not found.")
            return 1
        
        print(f"Versions for {skill_name}:")
        print()
        
        for version in skill.available_versions:
            info = skill.get_version_info(version)
            if info:
                marker = " (current)" if version == skill.current_version else ""
                print(f"  {version}{marker}")
                
                capabilities = info.get('capabilities', {})
                caps = capabilities.get('capabilities', [])
                print(f"    Capabilities: {', '.join(caps[:3])}")
                if len(caps) > 3:
                    print(f"      ... and {len(caps) - 3} more")
                
                breaking = info.get('breaking_changes', [])
                if breaking:
                    print(f"    Breaking Changes: {len(breaking)}")
                print()
        
        return 0
    
    def check_updates(self, skill_name: Optional[str] = None) -> int:
        """Check for skill updates."""
        if skill_name:
            skills = [skill_name]
        else:
            skills = self.registry.list_skills()
        
        updates_found = False
        
        for skill_name in skills:
            skill = self.registry.get_skill(skill_name)
            if not skill:
                continue
            
            if skill.available_versions:
                latest = max(skill.available_versions, key=skill._parse_version)
                if skill._compare_versions(latest, skill.current_version) > 0:
                    print(f"Update available for {skill_name}:")
                    print(f"  Current: {skill.current_version}")
                    print(f"  Latest: {latest}")
                    updates_found = True
        
        if not updates_found:
            if skill_name:
                print(f"No updates available for {skill_name}.")
            else:
                print("No updates available for any skill.")
        
        return 0
    
    def check_compatibility(self, pipeline_config_path: str) -> int:
        """Check pipeline compatibility with available skills."""
        config_path = Path(pipeline_config_path)
        
        if not config_path.exists():
            print(f"Pipeline config not found: {pipeline_config_path}")
            return 1
        
        with open(config_path, 'r') as f:
            pipeline_config = json.load(f)
        
        report = self.checker.generate_compatibility_report(pipeline_config)
        
        print(f"Compatibility Report for: {report['pipeline']}")
        print(f"Overall Status: {'✓ Compatible' if report['compatible'] else '✗ Incompatible'}")
        print()
        
        if report['skills']:
            print("Skill Status:")
            for skill_name, skill_info in report['skills'].items():
                status_icon = "✓" if skill_info.get('status') == 'compatible' else "✗"
                print(f"  {status_icon} {skill_name}")
                print(f"    Current: {skill_info.get('current_version', 'N/A')}")
                
                if skill_info.get('update_available'):
                    print(f"    Update available: {skill_info['update_available']}")
                
                if skill_info.get('errors'):
                    print(f"    Errors:")
                    for error in skill_info.get('errors', []):
                        print(f"      - {error}")
                
                if skill_info.get('warnings'):
                    print(f"    Warnings:")
                    for warning in skill_info.get('warnings', []):
                        print(f"      - {warning}")
                print()
        
        if report['errors']:
            print("Errors:")
            for error in report['errors']:
                print(f"  - {error}")
            print()
        
        if report['warnings']:
            print("Warnings:")
            for warning in report['warnings']:
                print(f"  - {warning}")
        
        return 0 if report['compatible'] else 1
    
    def find_skill_for_capability(self, capability: str) -> int:
        """Find skills that provide a specific capability."""
        results = self.registry.find_skill_for_capability(capability)
        
        if not results:
            print(f"No skills found providing capability: {capability}")
            return 0
        
        print(f"Skills providing '{capability}':")
        print()
        
        for skill_name, version in results:
            print(f"  {skill_name} v{version}")
        
        return 0
    
    def validate_workflow_state(self, state_path: str) -> int:
        """Validate workflow state against current skill versions."""
        state_file = Path(state_path)
        
        if not state_file.exists():
            print(f"Workflow state not found: {state_path}")
            return 1
        
        with open(state_file, 'r') as f:
            workflow_state = json.load(f)
        
        is_valid, errors = self.resolver.validate_workflow_state_compatibility(workflow_state)
        
        if is_valid:
            print("✓ Workflow state is compatible with current skill versions.")
            return 0
        else:
            print("✗ Workflow state has compatibility issues:")
            for error in errors:
                print(f"  - {error}")
            return 1


def main():
    parser = argparse.ArgumentParser(
        description='Skill Management CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List commands
    list_parser = subparsers.add_parser('list', help='List all available skills')
    list_parser.add_argument('--details', action='store_true', help='Show detailed information')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show skill information')
    info_parser.add_argument('skill', help='Skill name')
    
    # Versions command
    versions_parser = subparsers.add_parser('versions', help='List skill versions')
    versions_parser.add_argument('skill', help='Skill name')
    
    # Check updates command
    updates_parser = subparsers.add_parser('check-updates', help='Check for skill updates')
    updates_parser.add_argument('--skill', help='Specific skill to check (default: all)')
    
    # Compatibility command
    compat_parser = subparsers.add_parser('check-compatibility', help='Check pipeline compatibility')
    compat_parser.add_argument('config', help='Pipeline config file path')
    
    # Find capability command
    find_parser = subparsers.add_parser('find', help='Find skills by capability')
    find_parser.add_argument('capability', help='Capability to search for')
    
    # Validate state command
    validate_parser = subparsers.add_parser('validate-state', help='Validate workflow state')
    validate_parser.add_argument('state', help='Workflow state file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    cli = SkillCLI()
    
    if args.command == 'list':
        return cli.list_skills(args.details)
    elif args.command == 'info':
        return cli.skill_info(args.skill)
    elif args.command == 'versions':
        return cli.skill_versions(args.skill)
    elif args.command == 'check-updates':
        return cli.check_updates(args.skill)
    elif args.command == 'check-compatibility':
        return cli.check_compatibility(args.config)
    elif args.command == 'find':
        return cli.find_skill_for_capability(args.capability)
    elif args.command == 'validate-state':
        return cli.validate_workflow_state(args.state)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())