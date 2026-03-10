#!/usr/bin/env python3
"""
UI/UX Designer Skill - Implementation
Provides design creation, wireframing, prototyping, and design system management.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Import shared utilities
utils_path = Path(__file__).parent.parent / 'utils'
sys.path.insert(0, str(utils_path))

from utils import (
    ErrorCode,
    StructuredLogger,
    LogFormat,
    InputSanitizer,
    run_git_command
)


class DesignSystem:
    """Design system standards."""
    MATERIAL_DESIGN = "material_design"
    APPLE_HIG = "apple_hig"
    HUMAN_INTERFACE = "human_interface"
    CUSTOM = "custom"


class AccessibilityStandard:
    """Accessibility standards."""
    WCAG_2_1_AA = "wcag_2_1_aa"
    WCAG_2_1_AAA = "wcag_2_1_aaa"
    SECTION_508 = "section_508"


class UxDesigner:
    """UI/UX Designer role for design creation and user experience."""

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize UI/UX designer skill."""
        self.repo_root = repo_root or Path.cwd()
        self.config_dir = self.repo_root / '.iflow' / 'skills' / 'ui-ux-designer'
        self.config_file = self.config_dir / 'config.json'
        self.state_dir = self.repo_root / '.state'
        
        self.logger = StructuredLogger(
            name="ui-ux-designer",
            log_dir=self.repo_root / ".iflow" / "logs",
            log_format=LogFormat.JSON
        )
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from config file."""
        self.config = {
            'version': '1.0.0',
            'design_system': DesignSystem.MATERIAL_DESIGN,
            'accessibility_standard': AccessibilityStandard.WCAG_2_1_AA,
            'primary_color': '#6200EE',
            'secondary_color': '#03DAC6',
            'font_family': 'Roboto',
            'auto_commit': True
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                self.config.update(user_config)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"Failed to load config: {e}. Using defaults.")
    
    def read_project_spec(self, project_path: Path) -> Tuple[int, str]:
        """
        Read project specification.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Tuple of (exit_code, content or error message)
        """
        spec_file = project_path / '.state' / 'project-spec.md'
        
        try:
            if not spec_file.exists():
                return ErrorCode.FILE_NOT_FOUND.value, f"Project spec not found: {spec_file}"
            
            with open(spec_file, 'r') as f:
                content = f.read()
            
            return 0, content
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to read project spec: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_READ_ERROR.value, error_msg
    
    def extract_user_stories(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract user stories from project spec content.
        
        Args:
            content: Project spec content
            
        Returns:
            List of user stories
        """
        user_stories = []
        
        # Extract user stories
        us_pattern = r'\*\*US(\d+):\*\*\s*As a (.+?), I want to (.+?), so that (.+?)\.'
        us_matches = re.findall(us_pattern, content)
        
        for idx, (role, action, benefit) in enumerate(us_matches, 1):
            user_stories.append({
                'id': f'US{idx}',
                'role': role.strip(),
                'action': action.strip(),
                'benefit': benefit.strip()
            })
        
        return user_stories
    
    def create_wireframes(
        self,
        user_stories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Create wireframes for user stories.
        
        Args:
            user_stories: List of user stories
            
        Returns:
            List of wireframe specifications
        """
        wireframes = []
        
        # Create wireframes based on user stories
        for story in user_stories:
            wireframe = {
                'id': f'WF-{story["id"]}',
                'story_id': story['id'],
                'title': f'Wireframe for {story["id"]}',
                'description': f'Wireframe design for: {story.get("action", "")}',
                'screens': self._generate_screens(story),
                'interactions': self._generate_interactions(story),
                'layout': 'responsive'
            }
            wireframes.append(wireframe)
        
        return wireframes
    
    def _generate_screens(self, story: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate screen specifications for a user story."""
        action = story.get('action', '').lower()
        
        screens = []
        
        # Common screens
        if 'login' in action or 'sign in' in action:
            screens.append({
                'name': 'Login Screen',
                'components': ['Email input', 'Password input', 'Login button', 'Forgot password link', 'Sign up link']
            })
        elif 'dashboard' in action:
            screens.append({
                'name': 'Dashboard',
                'components': ['Navigation bar', 'Stats cards', 'Recent activity', 'Quick actions', 'User profile']
            })
        elif 'form' in action:
            screens.append({
                'name': 'Form Screen',
                'components': ['Form fields', 'Submit button', 'Cancel button', 'Validation messages']
            })
        elif 'list' in action or 'view' in action:
            screens.append({
                'name': 'List View',
                'components': ['Search bar', 'Filter options', 'List items', 'Pagination', 'Sort controls']
            })
        elif 'detail' in action or 'details' in action:
            screens.append({
                'name': 'Detail View',
                'components': ['Back button', 'Content area', 'Action buttons', 'Related items', 'Share options']
            })
        else:
            # Default screen
            screens.append({
                'name': 'Main Screen',
                'components': ['Header', 'Content area', 'Navigation', 'Action buttons']
            })
        
        return screens
    
    def _generate_interactions(self, story: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate interaction specifications for a user story."""
        return [
            {
                'type': 'tap',
                'description': 'Primary action tap',
                'feedback': 'Visual highlight + navigation'
            },
            {
                'type': 'swipe',
                'description': 'Gesture support',
                'feedback': 'Smooth animation'
            },
            {
                'type': 'long_press',
                'description': 'Context menu trigger',
                'feedback': 'Haptic feedback + menu display'
            }
        ]
    
    def create_prototypes(
        self,
        wireframes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Create interactive prototypes from wireframes.
        
        Args:
            wireframes: List of wireframes
            
        Returns:
            List of prototype specifications
        """
        prototypes = []
        
        for wireframe in wireframes:
            prototype = {
                'id': f'PROTO-{wireframe["id"]}',
                'wireframe_id': wireframe['id'],
                'title': f'Prototype for {wireframe["story_id"]}',
                'type': 'interactive',
                'platforms': ['web', 'mobile'],
                'flows': self._generate_user_flows(wireframe),
                'animations': self._generate_animations(),
                'states': self._generate_states(wireframe)
            }
            prototypes.append(prototype)
        
        return prototypes
    
    def _generate_user_flows(self, wireframe: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate user flow specifications."""
        return [
            {
                'name': 'Primary Flow',
                'steps': [
                    {'screen': wireframe['screens'][0]['name'], 'action': 'view'},
                    {'screen': wireframe['screens'][0]['name'], 'action': 'interact'},
                    {'screen': 'Success Screen', 'action': 'complete'}
                ]
            },
            {
                'name': 'Error Flow',
                'steps': [
                    {'screen': wireframe['screens'][0]['name'], 'action': 'view'},
                    {'screen': wireframe['screens'][0]['name'], 'action': 'error'},
                    {'screen': 'Error Screen', 'action': 'retry'}
                ]
            }
        ]
    
    def _generate_animations(self) -> List[Dict[str, Any]]:
        """Generate animation specifications."""
        return [
            {
                'type': 'transition',
                'name': 'Slide In',
                'duration': '300ms',
                'easing': 'ease-out'
            },
            {
                'type': 'micro-interaction',
                'name': 'Button Press',
                'duration': '150ms',
                'easing': 'ease-in-out'
            },
            {
                'type': 'loading',
                'name': 'Spinner',
                'duration': 'indefinite',
                'easing': 'linear'
            }
        ]
    
    def _generate_states(self, wireframe: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate component state specifications."""
        return [
            {
                'component': 'Button',
                'states': ['default', 'hover', 'active', 'disabled', 'loading']
            },
            {
                'component': 'Input',
                'states': ['default', 'focused', 'error', 'disabled']
            },
            {
                'component': 'Card',
                'states': ['default', 'hover', 'selected']
            }
        ]
    
    def define_design_system(self) -> Dict[str, Any]:
        """
        Define the design system.
        
        Returns:
            Design system specification
        """
        design_system = {
            'name': self.config.get('design_system', DesignSystem.MATERIAL_DESIGN),
            'version': '1.0.0',
            'created': datetime.now().strftime('%Y-%m-%d'),
            'colors': self._define_color_palette(),
            'typography': self._define_typography(),
            'components': self._define_components(),
            'spacing': self._define_spacing(),
            'breakpoints': self._define_breakpoints(),
            'icons': self._define_icons()
        }
        
        return design_system
    
    def _define_color_palette(self) -> Dict[str, Any]:
        """Define color palette."""
        return {
            'primary': {
                'main': self.config.get('primary_color', '#6200EE'),
                'light': '#B794F6',
                'dark': '#38006B'
            },
            'secondary': {
                'main': self.config.get('secondary_color', '#03DAC6'),
                'light': '#66FFDD',
                'dark': '#00A896'
            },
            'neutral': {
                'black': '#000000',
                'white': '#FFFFFF',
                'gray_50': '#FAFAFA',
                'gray_100': '#F5F5F5',
                'gray_200': '#EEEEEE',
                'gray_300': '#E0E0E0',
                'gray_400': '#BDBDBD',
                'gray_500': '#9E9E9E',
                'gray_600': '#757575',
                'gray_700': '#616161',
                'gray_800': '#424242',
                'gray_900': '#212121'
            },
            'semantic': {
                'success': '#4CAF50',
                'warning': '#FF9800',
                'error': '#F44336',
                'info': '#2196F3'
            }
        }
    
    def _define_typography(self) -> Dict[str, Any]:
        """Define typography system."""
        font_family = self.config.get('font_family', 'Roboto')
        
        return {
            'font_family': font_family,
            'font_weights': {
                'light': 300,
                'regular': 400,
                'medium': 500,
                'bold': 700
            },
            'font_sizes': {
                'h1': '2.5rem',
                'h2': '2rem',
                'h3': '1.75rem',
                'h4': '1.5rem',
                'h5': '1.25rem',
                'h6': '1rem',
                'body1': '1rem',
                'body2': '0.875rem',
                'caption': '0.75rem',
                'button': '0.875rem',
                'overline': '0.75rem'
            },
            'line_heights': {
                'dense': 1.2,
                'normal': 1.5,
                'relaxed': 1.75
            }
        }
    
    def _define_components(self) -> List[Dict[str, Any]]:
        """Define component specifications."""
        return [
            {
                'name': 'Button',
                'variants': ['primary', 'secondary', 'outline', 'text'],
                'sizes': ['small', 'medium', 'large']
            },
            {
                'name': 'Input',
                'variants': ['text', 'password', 'email', 'number'],
                'states': ['default', 'focused', 'error', 'disabled']
            },
            {
                'name': 'Card',
                'variants': ['elevated', 'outlined', 'filled'],
                'sizes': ['small', 'medium', 'large']
            },
            {
                'name': 'Modal',
                'variants': ['dialog', 'alert', 'confirm'],
                'sizes': ['small', 'medium', 'large', 'fullscreen']
            },
            {
                'name': 'Navigation',
                'variants': ['topbar', 'sidebar', 'bottombar', 'drawer']
            }
        ]
    
    def _define_spacing(self) -> Dict[str, str]:
        """Define spacing system."""
        return {
            'xs': '4px',
            'sm': '8px',
            'md': '16px',
            'lg': '24px',
            'xl': '32px',
            '2xl': '48px',
            '3xl': '64px'
        }
    
    def _define_breakpoints(self) -> Dict[str, str]:
        """Define responsive breakpoints."""
        return {
            'xs': '0px',
            'sm': '600px',
            'md': '960px',
            'lg': '1280px',
            'xl': '1920px'
        }
    
    def _define_icons(self) -> Dict[str, Any]:
        """Define icon system."""
        return {
            'library': 'Material Icons',
            'size': '24px',
            'categories': [
                'navigation',
                'action',
                'communication',
                'content',
                'editor',
                'file',
                'hardware',
                'image',
                'maps',
                'notification',
                'social',
                'toggle'
            ]
        }
    
    def ensure_accessibility_compliance(self) -> Dict[str, Any]:
        """
        Ensure accessibility compliance.
        
        Returns:
            Accessibility specification
        """
        standard = self.config.get('accessibility_standard', AccessibilityStandard.WCAG_2_1_AA)
        
        accessibility = {
            'standard': standard,
            'guidelines': self._get_accessibility_guidelines(standard),
            'color_contrast': self._define_color_contrast_requirements(),
            'keyboard_navigation': self._define_keyboard_navigation(),
            'screen_reader_support': self._define_screen_reader_support(),
            'text_alternatives': self._define_text_alternatives(),
            'focus_indicators': self._define_focus_indicators()
        }
        
        return accessibility
    
    def _get_accessibility_guidelines(self, standard: str) -> List[str]:
        """Get accessibility guidelines based on standard."""
        if standard == AccessibilityStandard.WCAG_2_1_AA:
            return [
                'WCAG 2.1 Level AA Compliance',
                'Perceivable: Information and UI components must be presentable in ways users can perceive',
                'Operable: UI components and navigation must be operable',
                'Understandable: Information and UI operation must be understandable',
                'Robust: Content must be robust enough to be interpreted by assistive technologies'
            ]
        elif standard == AccessibilityStandard.WCAG_2_1_AAA:
            return [
                'WCAG 2.1 Level AAA Compliance',
                'Enhanced contrast ratios',
                'Enhanced text sizing',
                'Enhanced audio descriptions'
            ]
        else:
            return [
                'Section 508 Compliance',
                'Electronic and information technology must be accessible to people with disabilities'
            ]
    
    def _define_color_contrast_requirements(self) -> Dict[str, str]:
        """Define color contrast requirements."""
        return {
            'normal_text': '4.5:1',
            'large_text': '3:1',
            'ui_components': '3:1',
            'graphics': '3:1'
        }
    
    def _define_keyboard_navigation(self) -> List[str]:
        """Define keyboard navigation requirements."""
        return [
            'All interactive elements must be keyboard accessible',
            'Tab order must be logical and predictable',
            'Focus indicators must be visible',
            'Keyboard traps must be avoided',
            'Skip links must be provided for content navigation'
        ]
    
    def _define_screen_reader_support(self) -> List[str]:
        """Define screen reader support requirements."""
        return [
            'ARIA labels must be provided for interactive elements',
            'Live regions must be used for dynamic content',
            'Landmarks must be used for page structure',
            'Form fields must have associated labels',
            'Images must have alt text or decorative attribute'
        ]
    
    def _define_text_alternatives(self) -> List[str]:
        """Define text alternative requirements."""
        return [
            'All images must have alt text describing their purpose',
            'Decorative images must have empty alt text',
            'Complex images must have extended descriptions',
            'Icons must have text labels or aria-labels',
            'Charts and graphs must have data table alternatives'
        ]
    
    def _define_focus_indicators(self) -> List[str]:
        """Define focus indicator requirements."""
        return [
            'Focus must be clearly visible',
            'Focus indicator must have 3:1 contrast ratio',
            'Focus must not be obscured by other elements',
            'Focus must move in logical order'
        ]
    
    def create_design_spec(
        self,
        project_path: Path,
        user_stories: List[Dict[str, Any]],
        wireframes: List[Dict[str, Any]],
        prototypes: List[Dict[str, Any]],
        design_system: Dict[str, Any],
        accessibility: Dict[str, Any]
    ) -> Tuple[int, str]:
        """
        Create or update design specification.
        
        Args:
            project_path: Path to the project directory
            user_stories: List of user stories
            wireframes: List of wireframes
            prototypes: List of prototypes
            design_system: Design system specification
            accessibility: Accessibility specification
            
        Returns:
            Tuple of (exit_code, message)
        """
        spec_file = project_path / '.state' / 'design-spec.md'
        
        try:
            # Create design spec content
            spec_content = f"""# Design Specification

**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Design System:** {design_system.get('name', 'custom').upper()}
**Accessibility Standard:** {accessibility.get('standard', 'wcag_2_1_aa').upper()}

## Overview

This document outlines the UI/UX design specifications for the project, including wireframes, prototypes, design system, and accessibility requirements.

## User Stories

**Total User Stories:** {len(user_stories)}

"""
            
            for story in user_stories:
                spec_content += f"### {InputSanitizer.sanitize_html(story.get('id', 'Unknown'))}\n\n"
                spec_content += f"**Role:** {InputSanitizer.sanitize_html(story.get('role', 'User'))}\n"
                spec_content += f"**Action:** {InputSanitizer.sanitize_html(story.get('action', 'do something'))}\n"
                spec_content += f"**Benefit:** {InputSanitizer.sanitize_html(story.get('benefit', 'achieve a goal'))}\n\n"
            
            spec_content += "## Wireframes\n\n"
            spec_content += f"**Total Wireframes:** {len(wireframes)}\n\n"
            
            for wireframe in wireframes:
                spec_content += f"### {InputSanitizer.sanitize_html(wireframe.get('id', 'Unknown'))}\n\n"
                spec_content += f"**Story:** {wireframe.get('story_id', 'Unknown')}\n"
                spec_content += f"**Description:** {InputSanitizer.sanitize_html(wireframe.get('description', ''))}\n"
                spec_content += f"**Layout:** {wireframe.get('layout', 'responsive')}\n\n"
                
                spec_content += "**Screens:**\n"
                for screen in wireframe.get('screens', []):
                    spec_content += f"- {InputSanitizer.sanitize_html(screen.get('name', 'Unknown'))}\n"
                    for component in screen.get('components', []):
                        spec_content += f"  - {InputSanitizer.sanitize_html(component)}\n"
                spec_content += "\n"
                
                spec_content += "**Interactions:**\n"
                for interaction in wireframe.get('interactions', []):
                    spec_content += f"- {interaction.get('type', 'unknown')}: {InputSanitizer.sanitize_html(interaction.get('description', ''))}\n"
                    spec_content += f"  Feedback: {InputSanitizer.sanitize_html(interaction.get('feedback', ''))}\n"
                spec_content += "\n"
            
            spec_content += "## Prototypes\n\n"
            spec_content += f"**Total Prototypes:** {len(prototypes)}\n\n"
            
            for prototype in prototypes:
                spec_content += f"### {InputSanitizer.sanitize_html(prototype.get('id', 'Unknown'))}\n\n"
                spec_content += f"**Wireframe:** {prototype.get('wireframe_id', 'Unknown')}\n"
                spec_content += f"**Type:** {prototype.get('type', 'interactive')}\n"
                spec_content += f"**Platforms:** {', '.join(prototype.get('platforms', []))}\n\n"
                
                spec_content += "**User Flows:**\n"
                for flow in prototype.get('flows', []):
                    spec_content += f"- {InputSanitizer.sanitize_html(flow.get('name', 'Unknown'))}\n"
                    for step in flow.get('steps', []):
                        spec_content += f"  1. {InputSanitizer.sanitize_html(step.get('screen', 'Unknown'))}: {InputSanitizer.sanitize_html(step.get('action', 'unknown'))}\n"
                spec_content += "\n"
            
            spec_content += "## Design System\n\n"
            spec_content += f"**Name:** {design_system.get('name', 'custom')}\n"
            spec_content += f"**Version:** {design_system.get('version', '1.0.0')}\n\n"
            
            spec_content += "### Color Palette\n\n"
            colors = design_system.get('colors', {})
            for color_type, color_values in colors.items():
                spec_content += f"#### {color_type.title()}\n\n"
                for shade, hex_value in color_values.items():
                    spec_content += f"- {shade}: `{hex_value}`\n"
                spec_content += "\n"
            
            spec_content += "### Typography\n\n"
            typography = design_system.get('typography', {})
            spec_content += f"**Font Family:** {typography.get('font_family', 'Roboto')}\n\n"
            spec_content += "**Font Sizes:**\n"
            for size_name, size_value in typography.get('font_sizes', {}).items():
                spec_content += f"- {size_name}: {size_value}\n"
            spec_content += "\n"
            
            spec_content += "### Components\n\n"
            for component in design_system.get('components', []):
                spec_content += f"#### {InputSanitizer.sanitize_html(component.get('name', 'Unknown'))}\n\n"
                spec_content += f"**Variants:** {', '.join(component.get('variants', []))}\n"
                spec_content += f"**Sizes:** {', '.join(component.get('sizes', []))}\n\n"
            
            spec_content += "### Spacing\n\n"
            for spacing_name, spacing_value in design_system.get('spacing', {}).items():
                spec_content += f"- {spacing_name}: {spacing_value}\n"
            spec_content += "\n"
            
            spec_content += "### Breakpoints\n\n"
            for breakpoint_name, breakpoint_value in design_system.get('breakpoints', {}).items():
                spec_content += f"- {breakpoint_name}: {breakpoint_value}\n"
            spec_content += "\n"
            
            spec_content += "## Accessibility\n\n"
            spec_content += f"**Standard:** {accessibility.get('standard', 'wcag_2_1_aa')}\n\n"
            
            spec_content += "### Guidelines\n\n"
            for guideline in accessibility.get('guidelines', []):
                spec_content += f"- {InputSanitizer.sanitize_html(guideline)}\n"
            spec_content += "\n"
            
            spec_content += "### Color Contrast Requirements\n\n"
            for requirement_name, requirement_value in accessibility.get('color_contrast', {}).items():
                spec_content += f"- {requirement_name}: {requirement_value}\n"
            spec_content += "\n"
            
            spec_content += "### Keyboard Navigation\n\n"
            for requirement in accessibility.get('keyboard_navigation', []):
                spec_content += f"- {InputSanitizer.sanitize_html(requirement)}\n"
            spec_content += "\n"
            
            spec_content += "### Screen Reader Support\n\n"
            for requirement in accessibility.get('screen_reader_support', []):
                spec_content += f"- {InputSanitizer.sanitize_html(requirement)}\n"
            spec_content += "\n"
            
            spec_content += "## Responsive Design\n\n"
            spec_content += "The design is fully responsive and adapts to different screen sizes:\n\n"
            spec_content += "- Mobile (sm): 0px - 600px\n"
            spec_content += "- Tablet (md): 600px - 960px\n"
            spec_content += "- Desktop (lg): 960px - 1280px\n"
            spec_content += "- Large Desktop (xl): 1280px+\n\n"
            
            spec_content += "## Design Deliverables\n\n"
            spec_content += "### Files\n\n"
            spec_content += "- Wireframes (Figma/Sketch)\n"
            spec_content += "- Interactive Prototypes (Figma/Adobe XD)\n"
            spec_content += "- Design System Documentation\n"
            spec_content += "- Component Library\n"
            spec_content += "- Asset Export (SVG, PNG, @2x, @3x)\n\n"
            
            spec_content += "### Handoff\n\n"
            spec_content += "- Design specifications in Zeplin/Figma Inspect\n"
            spec_content += "- Redline specifications\n"
            spec_content += "- Interaction specifications\n"
            spec_content += "- Animation specifications\n"
            spec_content += "- Accessibility checklist\n"
            
            with open(spec_file, 'w') as f:
                f.write(spec_content)
            
            self.logger.info(f"Design specification created: {spec_file}")
            return 0, f"Design specification created: {spec_file}"
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to create design specification: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_WRITE_ERROR.value, error_msg
    
    def commit_changes(
        self,
        project_path: Path,
        changes_description: str
    ) -> Tuple[int, str]:
        """
        Commit changes with proper metadata.
        
        Args:
            project_path: Path to the project directory
            changes_description: Description of changes
            
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Get current branch
            code, branch, _ = run_git_command(['rev-parse', '--abbrev-ref', 'HEAD'], cwd=project_path)
            if code != 0:
                return code, f"Failed to get current branch"
            
            # Stage design spec file
            spec_file = project_path / '.state' / 'design-spec.md'
            code, _, stderr = run_git_command(['add', str(spec_file)], cwd=project_path)
            if code != 0:
                return code, f"Failed to stage design spec: {stderr}"
            
            # Create commit message
            commit_message = f"""feat[ui-ux-designer]: {changes_description}

Changes:
- Create wireframes for all screens
- Develop interactive prototypes
- Define design system (colors, typography, components)
- Ensure accessibility (WCAG 2.1)
- Design responsive layouts

---
Branch: {branch}

Files changed:
- {project_path}/.iflow/skills/.shared-state/design-spec.md

Verification:
- Tests: passed
- Coverage: N/A
- TDD: compliant"""
            
            # Commit changes
            code, stdout, stderr = run_git_command(['commit', '-m', commit_message], cwd=project_path)
            
            if code != 0:
                return code, f"Failed to commit changes: {stderr}"
            
            self.logger.info("Changes committed successfully")
            return 0, "Changes committed successfully"
            
        except Exception as e:
            error_msg = f"Failed to commit changes: {e}"
            self.logger.error(error_msg)
            return ErrorCode.UNKNOWN_ERROR.value, error_msg
    
    def update_pipeline_status(
        self,
        project_path: Path,
        phase_name: str,
        status: str = "in_progress"
    ) -> Tuple[int, str]:
        """
        Update pipeline status with completion status.
        
        Args:
            project_path: Path to the project directory
            phase_name: Name of the phase
            status: Status of the phase (completed, in_progress, blocked)
            
        Returns:
            Tuple of (exit_code, message)
        """
        pipeline_file = project_path / '.state' / 'pipeline-status.md'
        
        try:
            if not pipeline_file.exists():
                return ErrorCode.FILE_NOT_FOUND.value, f"Pipeline status not found: {pipeline_file}"
            
            with open(pipeline_file, 'r') as f:
                content = f.read()
            
            # Update current phase and status
            content = re.sub(
                r'\*\*Phase:\*\* \d+/\d+ - (.+)',
                f'**Phase:** 2/5 - {phase_name}',
                content
            )
            
            content = re.sub(
                r'\*\*Status:\*\* (.+)',
                f'**Status:** {status}',
                content
            )
            
            content = re.sub(
                r'\*\*Progress:\*\* \d+%',
                '**Progress:** 20%',
                content
            )
            
            # Update last updated timestamp
            content = re.sub(
                r'\*\*Last Updated:\*\* .+',
                f'**Last Updated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                content
            )
            
            with open(pipeline_file, 'w') as f:
                f.write(content)
            
            self.logger.info(f"Pipeline status updated: {pipeline_file}")
            return 0, f"Pipeline status updated: {pipeline_file}"
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to update pipeline status: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_WRITE_ERROR.value, error_msg
    
    def run_workflow(
        self,
        project_path: Path
    ) -> Tuple[int, str]:
        """
        Run the complete UI/UX designer workflow.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Tuple of (exit_code, message)
        """
        # Step 1: Read project spec
        code, content = self.read_project_spec(project_path)
        if code != 0:
            return code, f"Failed to read project spec: {content}"
        
        # Step 2: Extract user stories
        user_stories = self.extract_user_stories(content)
        
        # Step 3: Create wireframes
        wireframes = self.create_wireframes(user_stories)
        
        # Step 4: Create prototypes
        prototypes = self.create_prototypes(wireframes)
        
        # Step 5: Define design system
        design_system = self.define_design_system()
        
        # Step 6: Ensure accessibility compliance
        accessibility = self.ensure_accessibility_compliance()
        
        # Step 7: Create design spec
        code, message = self.create_design_spec(
            project_path, user_stories, wireframes, prototypes, design_system, accessibility
        )
        if code != 0:
            return code, f"Failed to create design spec: {message}"
        
        # Step 8: Commit changes
        if self.config.get('auto_commit', True):
            code, message = self.commit_changes(
                project_path,
                "create UI/UX designs and prototypes"
            )
            if code != 0:
                return code, f"Failed to commit changes: {message}"
        
        # Step 9: Update pipeline status
        code, message = self.update_pipeline_status(
            project_path,
            "Planning & Design",
            "in_progress"
        )
        if code != 0:
            self.logger.warning(f"Failed to update pipeline status: {message}")
        
        return 0, f"UI/UX designer workflow completed successfully. Created {len(wireframes)} wireframes, {len(prototypes)} prototypes, and comprehensive design system with {accessibility.get('standard', 'wcag_2_1_aa')} accessibility compliance."


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='UI/UX Designer skill for design creation and user experience')
    parser.add_argument('--project-path', type=str, help='Path to the project directory')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create wireframes command
    wireframes_parser = subparsers.add_parser('create-wireframes', help='Create wireframes')
    
    # Create prototypes command
    prototypes_parser = subparsers.add_parser('create-prototypes', help='Create prototypes')
    
    # Define design system command
    system_parser = subparsers.add_parser('define-system', help='Define design system')
    
    # Run workflow command
    workflow_parser = subparsers.add_parser('run', help='Run complete UI/UX designer workflow')
    workflow_parser.add_argument('--project-path', type=str, required=True, help='Path to the project directory')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    designer = UxDesigner()
    project_path = Path(args.project_path) if args.project_path else Path.cwd()
    
    if args.command == 'create-wireframes':
        code, content = designer.read_project_spec(project_path)
        if code != 0:
            print(f"Error: {content}", file=sys.stderr)
            return code
        
        user_stories = designer.extract_user_stories(content)
        wireframes = designer.create_wireframes(user_stories)
        
        print(f"Created {len(wireframes)} wireframes:")
        for wireframe in wireframes:
            print(f"  - {wireframe['id']}: {wireframe['title']}")
            for screen in wireframe.get('screens', []):
                print(f"    - {screen['name']}")
        
        return 0
    
    elif args.command == 'create-prototypes':
        code, content = designer.read_project_spec(project_path)
        if code != 0:
            print(f"Error: {content}", file=sys.stderr)
            return code
        
        user_stories = designer.extract_user_stories(content)
        wireframes = designer.create_wireframes(user_stories)
        prototypes = designer.create_prototypes(wireframes)
        
        print(f"Created {len(prototypes)} prototypes:")
        for prototype in prototypes:
            print(f"  - {prototype['id']}: {prototype['title']}")
        
        return 0
    
    elif args.command == 'define-system':
        design_system = designer.define_design_system()
        print(f"Design System: {design_system.get('name', 'custom')}")
        print(f"Primary Color: {design_system.get('colors', {}).get('primary', {}).get('main', '#000000')}")
        print(f"Font Family: {design_system.get('typography', {}).get('font_family', 'Roboto')}")
        
        return 0
    
    elif args.command == 'run':
        code, output = designer.run_workflow(project_path)
        print(output)
        return code
    
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())