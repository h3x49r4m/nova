"""Color Output - Provides colored console output for CLI.

This module provides colored console output with support for multiple
color schemes, styles, and platform compatibility.
"""

import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class Color(Enum):
    """ANSI color codes."""
    BLACK = "30"
    RED = "31"
    GREEN = "32"
    YELLOW = "33"
    BLUE = "34"
    MAGENTA = "35"
    CYAN = "36"
    WHITE = "37"
    BRIGHT_BLACK = "90"
    BRIGHT_RED = "91"
    BRIGHT_GREEN = "92"
    BRIGHT_YELLOW = "93"
    BRIGHT_BLUE = "94"
    BRIGHT_MAGENTA = "95"
    BRIGHT_CYAN = "96"
    BRIGHT_WHITE = "97"


class Style(Enum):
    """ANSI style codes."""
    RESET = "0"
    BOLD = "1"
    DIM = "2"
    ITALIC = "3"
    UNDERLINE = "4"
    BLINK = "5"
    REVERSE = "7"
    HIDDEN = "8"
    STRIKETHROUGH = "9"


@dataclass
class ColorTheme:
    """Color theme for output."""
    name: str
    success: Color = Color.GREEN
    error: Color = Color.RED
    warning: Color = Color.YELLOW
    info: Color = Color.BLUE
    debug: Color = Color.BRIGHT_BLACK
    primary: Color = Color.CYAN
    secondary: Color = Color.MAGENTA
    accent: Color = Color.BRIGHT_BLUE
    muted: Color = Color.BRIGHT_BLACK
    styles: Dict[str, List[Style]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "success": self.success.value,
            "error": self.error.value,
            "warning": self.warning.value,
            "info": self.info.value,
            "debug": self.debug.value,
            "primary": self.primary.value,
            "secondary": self.secondary.value,
            "accent": self.accent.value,
            "muted": self.muted.value,
            "styles": {k: [s.value for s in v] for k, v in self.styles.items()}
        }


# Predefined themes
DEFAULT_THEME = ColorTheme(
    name="default",
    success=Color.GREEN,
    error=Color.RED,
    warning=Color.YELLOW,
    info=Color.BLUE,
    debug=Color.BRIGHT_BLACK,
    primary=Color.CYAN,
    secondary=Color.MAGENTA,
    accent=Color.BRIGHT_BLUE,
    muted=Color.BRIGHT_BLACK,
    styles={
        "title": [Style.BOLD],
        "subtitle": [Style.UNDERLINE],
        "emphasis": [Style.BOLD],
        "code": [Style.DIM],
        "link": [Style.UNDERLINE]
    }
)

DARK_THEME = ColorTheme(
    name="dark",
    success=Color.BRIGHT_GREEN,
    error=Color.BRIGHT_RED,
    warning=Color.BRIGHT_YELLOW,
    info=Color.BRIGHT_BLUE,
    debug=Color.BRIGHT_BLACK,
    primary=Color.BRIGHT_CYAN,
    secondary=Color.BRIGHT_MAGENTA,
    accent=Color.BRIGHT_WHITE,
    muted=Color.BRIGHT_BLACK,
    styles={
        "title": [Style.BOLD],
        "subtitle": [Style.UNDERLINE],
        "emphasis": [Style.BOLD],
        "code": [Style.DIM],
        "link": [Style.UNDERLINE]
    }
)

LIGHT_THEME = ColorTheme(
    name="light",
    success=Color.GREEN,
    error=Color.RED,
    warning=Color.YELLOW,
    info=Color.BLUE,
    debug=Color.BLACK,
    primary=Color.CYAN,
    secondary=Color.MAGENTA,
    accent=Color.BLUE,
    muted=Color.BLACK,
    styles={
        "title": [Style.BOLD],
        "subtitle": [Style.UNDERLINE],
        "emphasis": [Style.BOLD],
        "code": [Style.DIM],
        "link": [Style.UNDERLINE]
    }
)

MINIMAL_THEME = ColorTheme(
    name="minimal",
    success=Color.GREEN,
    error=Color.RED,
    warning=Color.YELLOW,
    info=Color.BLUE,
    debug=Color.BLACK,
    primary=Color.BLUE,
    secondary=Color.BLACK,
    accent=Color.CYAN,
    muted=Color.BLACK,
    styles={}
)


class ColorFormatter:
    """Formats text with colors and styles."""
    
    def __init__(
        self,
        theme: ColorTheme = DEFAULT_THEME,
        enabled: Optional[bool] = None
    ):
        """
        Initialize color formatter.
        
        Args:
            theme: Color theme to use
            enabled: Whether colors are enabled (auto-detect if None)
        """
        self.theme = theme
        self.enabled = enabled if enabled is not None else self._detect_color_support()
    
    def _detect_color_support(self) -> bool:
        """
        Detect if terminal supports colors.
        
        Returns:
            True if colors are supported
        """
        # Check if explicitly disabled
        if os.environ.get("NO_COLOR"):
            return False
        
        if os.environ.get("TERM") == "dumb":
            return False
        
        # Check if running in Windows
        if sys.platform == "win32":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                return kernel32.GetConsoleMode(kernel32.GetStdHandle(-11), 0) != 0
            except Exception as e:
                self.logger.debug(f"Failed to check Windows console mode: {e}")
                return False
        
        # Check if stdout is a TTY
        if not sys.stdout.isatty():
            return False
        
        # Check COLORTERM environment variable
        if os.environ.get("COLORTERM"):
            return True
        
        # Check TERM environment variable
        term = os.environ.get("TERM", "")
        if "color" in term or "256color" in term or "xterm" in term:
            return True
        
        return True
    
    def colorize(
        self,
        text: str,
        color: Optional[Color] = None,
        styles: Optional[List[Style]] = None
    ) -> str:
        """
        Apply colors and styles to text.
        
        Args:
            text: Text to colorize
            color: Color to apply
            styles: Styles to apply
            
        Returns:
            Colorized text
        """
        if not self.enabled or (not color and not styles):
            return text
        
        codes = []
        
        if color:
            codes.append(f"\033[{color.value}m")
        
        if styles:
            for style in styles:
                codes.append(f"\033[{style.value}m")
        
        if codes:
            prefix = "".join(codes)
            suffix = "\033[0m"
            return f"{prefix}{text}{suffix}"
        
        return text
    
    def success(self, text: str) -> str:
        """Format text as success."""
        return self.colorize(text, self.theme.success)
    
    def error(self, text: str) -> str:
        """Format text as error."""
        return self.colorize(text, self.theme.error)
    
    def warning(self, text: str) -> str:
        """Format text as warning."""
        return self.colorize(text, self.theme.warning)
    
    def info(self, text: str) -> str:
        """Format text as info."""
        return self.colorize(text, self.theme.info)
    
    def debug(self, text: str) -> str:
        """Format text as debug."""
        return self.colorize(text, self.theme.debug)
    
    def primary(self, text: str) -> str:
        """Format text as primary."""
        return self.colorize(text, self.theme.primary)
    
    def secondary(self, text: str) -> str:
        """Format text as secondary."""
        return self.colorize(text, self.theme.secondary)
    
    def accent(self, text: str) -> str:
        """Format text as accent."""
        return self.colorize(text, self.theme.accent)
    
    def muted(self, text: str) -> str:
        """Format text as muted."""
        return self.colorize(text, self.theme.muted)
    
    def title(self, text: str) -> str:
        """Format text as title."""
        styles = self.theme.styles.get("title", [Style.BOLD])
        return self.colorize(text, self.theme.primary, styles)
    
    def subtitle(self, text: str) -> str:
        """Format text as subtitle."""
        styles = self.theme.styles.get("subtitle", [Style.UNDERLINE])
        return self.colorize(text, self.theme.secondary, styles)
    
    def emphasis(self, text: str) -> str:
        """Format text with emphasis."""
        styles = self.theme.styles.get("emphasis", [Style.BOLD])
        return self.colorize(text, None, styles)
    
    def code(self, text: str) -> str:
        """Format text as code."""
        styles = self.theme.styles.get("code", [Style.DIM])
        return self.colorize(text, self.theme.muted, styles)
    
    def link(self, text: str) -> str:
        """Format text as link."""
        styles = self.theme.styles.get("link", [Style.UNDERLINE])
        return self.colorize(text, self.theme.info, styles)
    
    def custom(
        self,
        text: str,
        color: Color,
        styles: Optional[List[Style]] = None
    ) -> str:
        """
        Format text with custom color and styles.
        
        Args:
            text: Text to format
            color: Color to use
            styles: Styles to apply
            
        Returns:
            Formatted text
        """
        return self.colorize(text, color, styles)
    
    def set_theme(self, theme: ColorTheme):
        """
        Set the color theme.
        
        Args:
            theme: New color theme
        """
        self.theme = theme
    
    def enable(self):
        """Enable color output."""
        self.enabled = True
    
    def disable(self):
        """Disable color output."""
        self.enabled = False
    
    def is_enabled(self) -> bool:
        """
        Check if colors are enabled.
        
        Returns:
            True if colors are enabled
        """
        return self.enabled


class ColorConsole:
    """Provides colored console output methods."""
    
    def __init__(
        self,
        theme: ColorTheme = DEFAULT_THEME,
        enabled: Optional[bool] = None
    ):
        """
        Initialize color console.
        
        Args:
            theme: Color theme to use
            enabled: Whether colors are enabled
        """
        self.formatter = ColorFormatter(theme, enabled)
    
    def print(
        self,
        *args: Any,
        color: Optional[Color] = None,
        styles: Optional[List[Style]] = None,
        sep: str = " ",
        end: str = "\n",
        file=None,
        flush: bool = False
    ):
        """
        Print colored text.
        
        Args:
            *args: Arguments to print
            color: Color to apply
            styles: Styles to apply
            sep: Separator
            end: End string
            file: File to write to
            flush: Whether to flush
        """
        if file is None:
            file = sys.stdout
        
        formatted_args = []
        for arg in args:
            text = str(arg)
            if color or styles:
                text = self.formatter.colorize(text, color, styles)
            formatted_args.append(text)
        
        print(*formatted_args, sep=sep, end=end, file=file, flush=flush)
    
    def success(self, *args: Any, **kwargs):
        """Print success message."""
        formatted_args = [self.formatter.success(str(arg)) for arg in args]
        print(*formatted_args, **kwargs)
    
    def error(self, *args: Any, **kwargs):
        """Print error message."""
        formatted_args = [self.formatter.error(str(arg)) for arg in args]
        print(*formatted_args, file=sys.stderr, **kwargs)
    
    def warning(self, *args: Any, **kwargs):
        """Print warning message."""
        formatted_args = [self.formatter.warning(str(arg)) for arg in args]
        print(*formatted_args, file=sys.stderr, **kwargs)
    
    def info(self, *args: Any, **kwargs):
        """Print info message."""
        formatted_args = [self.formatter.info(str(arg)) for arg in args]
        print(*formatted_args, **kwargs)
    
    def debug(self, *args: Any, **kwargs):
        """Print debug message."""
        formatted_args = [self.formatter.debug(str(arg)) for arg in args]
        print(*formatted_args, **kwargs)
    
    def primary(self, *args: Any, **kwargs):
        """Print primary message."""
        formatted_args = [self.formatter.primary(str(arg)) for arg in args]
        print(*formatted_args, **kwargs)
    
    def secondary(self, *args: Any, **kwargs):
        """Print secondary message."""
        formatted_args = [self.formatter.secondary(str(arg)) for arg in args]
        print(*formatted_args, **kwargs)
    
    def accent(self, *args: Any, **kwargs):
        """Print accent message."""
        formatted_args = [self.formatter.accent(str(arg)) for arg in args]
        print(*formatted_args, **kwargs)
    
    def muted(self, *args: Any, **kwargs):
        """Print muted message."""
        formatted_args = [self.formatter.muted(str(arg)) for arg in args]
        print(*formatted_args, **kwargs)
    
    def title(self, *args: Any, **kwargs):
        """Print title."""
        formatted_args = [self.formatter.title(str(arg)) for arg in args]
        print(*formatted_args, **kwargs)
    
    def subtitle(self, *args: Any, **kwargs):
        """Print subtitle."""
        formatted_args = [self.formatter.subtitle(str(arg)) for arg in args]
        print(*formatted_args, **kwargs)
    
    def header(self, text: str, level: int = 1, **kwargs):
        """
        Print header with level.
        
        Args:
            text: Header text
            level: Header level (1-6)
            **kwargs: Additional print arguments
        """
        prefix = "#" * level
        if level == 1:
            print(self.formatter.title(f"{prefix} {text}"), **kwargs)
        elif level == 2:
            print(self.formatter.subtitle(f"{prefix} {text}"), **kwargs)
        else:
            print(f"{prefix} {text}", **kwargs)
    
    def separator(self, char: str = "-", length: int = 50, **kwargs):
        """
        Print separator line.
        
        Args:
            char: Character to use
            length: Length of separator
            **kwargs: Additional print arguments
        """
        print(self.formatter.muted(char * length), **kwargs)
    
    def bullet(self, text: str, level: int = 0, **kwargs):
        """
        Print bullet point.
        
        Args:
            text: Bullet text
            level: Indentation level
            **kwargs: Additional print arguments
        """
        indent = "  " * level
        bullets = ["•", "◦", "▪", "·"]
        bullet = bullets[min(level, len(bullets) - 1)]
        print(f"{indent}{bullet} {text}", **kwargs)
    
    def list(self, items: List[str], **kwargs):
        """
        Print list of items.
        
        Args:
            items: List of items to print
            **kwargs: Additional print arguments
        """
        for item in items:
            self.bullet(item, **kwargs)
    
    def key_value(self, key: str, value: Any, **kwargs):
        """
        Print key-value pair.
        
        Args:
            key: Key name
            value: Value
            **kwargs: Additional print arguments
        """
        print(
            f"{self.formatter.primary(key)}: {self.formatter.secondary(str(value))}",
            **kwargs
        )
    
    def progress(
        self,
        current: int,
        total: int,
        prefix: str = "",
        width: int = 50,
        **kwargs
    ):
        """
        Print progress bar.
        
        Args:
            current: Current progress
            total: Total items
            prefix: Prefix text
            width: Bar width
            **kwargs: Additional print arguments
        """
        percent = min(100, max(0, int(current / total * 100)) if total > 0 else 0)
        filled = int(width * current / total) if total > 0 else 0
        bar = self.formatter.success("█" * filled) + self.formatter.muted("░" * (width - filled))
        
        print(f"\r{prefix} {bar} {percent}%", end="", **kwargs)
        if current == total:
            print()  # New line when complete
    
    def table(
        self,
        headers: List[str],
        rows: List[List[str]],
        **kwargs
    ):
        """
        Print table.
        
        Args:
            headers: Column headers
            rows: Table rows
            **kwargs: Additional print arguments
        """
        # Calculate column widths
        all_rows = [headers] + rows
        col_widths = [
            max(len(str(row[i])) for row in all_rows)
            for i in range(len(headers))
        ]
        
        # Print header
        header_row = " | ".join(
            self.formatter.title(headers[i].ljust(col_widths[i]))
            for i in range(len(headers))
        )
        print(header_row, **kwargs)
        
        # Print separator
        separator = "-+-".join(
            self.formatter.muted("-" * col_widths[i])
            for i in range(len(headers))
        )
        print(separator, **kwargs)
        
        # Print rows
        for row in rows:
            formatted_row = " | ".join(
                self.formatter.secondary(str(row[i]).ljust(col_widths[i]))
                for i in range(len(row))
            )
            print(formatted_row, **kwargs)
    
    def set_theme(self, theme: ColorTheme):
        """
        Set the color theme.
        
        Args:
            theme: New color theme
        """
        self.formatter.set_theme(theme)
    
    def enable(self):
        """Enable color output."""
        self.formatter.enable()
    
    def disable(self):
        """Disable color output."""
        self.formatter.disable()
    
    def is_enabled(self) -> bool:
        """
        Check if colors are enabled.
        
        Returns:
            True if colors are enabled
        """
        return self.formatter.is_enabled()


# Global console instance
_global_console: Optional[ColorConsole] = None


def get_console(
    theme: ColorTheme = DEFAULT_THEME,
    enabled: Optional[bool] = None
) -> ColorConsole:
    """
    Get or create global console instance.
    
    Args:
        theme: Color theme to use
        enabled: Whether colors are enabled
        
    Returns:
        ColorConsole instance
    """
    global _global_console
    
    if _global_console is None:
        _global_console = ColorConsole(theme, enabled)
    
    return _global_console


def get_formatter(
    theme: ColorTheme = DEFAULT_THEME,
    enabled: Optional[bool] = None
) -> ColorFormatter:
    """
    Get color formatter.
    
    Args:
        theme: Color theme to use
        enabled: Whether colors are enabled
        
    Returns:
        ColorFormatter instance
    """
    return ColorFormatter(theme, enabled)


# Convenience functions using global console
def success(text: str) -> str:
    """Format text as success."""
    return get_console().formatter.success(text)


def error(text: str) -> str:
    """Format text as error."""
    return get_console().formatter.error(text)


def warning(text: str) -> str:
    """Format text as warning."""
    return get_console().formatter.warning(text)


def info(text: str) -> str:
    """Format text as info."""
    return get_console().formatter.info(text)


def debug(text: str) -> str:
    """Format text as debug."""
    return get_console().formatter.debug(text)


def primary(text: str) -> str:
    """Format text as primary."""
    return get_console().formatter.primary(text)


def secondary(text: str) -> str:
    """Format text as secondary."""
    return get_console().formatter.secondary(text)


def accent(text: str) -> str:
    """Format text as accent."""
    return get_console().formatter.accent(text)


def muted(text: str) -> str:
    """Format text as muted."""
    return get_console().formatter.muted(text)


def title(text: str) -> str:
    """Format text as title."""
    return get_console().formatter.title(text)


def subtitle(text: str) -> str:
    """Format text as subtitle."""
    return get_console().formatter.subtitle(text)


def code(text: str) -> str:
    """Format text as code."""
    return get_console().formatter.code(text)