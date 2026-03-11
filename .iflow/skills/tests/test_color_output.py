"""Tests for color_output module."""

import pytest
from pathlib import Path
import sys
from io import StringIO

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.color_output import (
    Color,
    Style,
    ColorTheme,
    ColorFormatter,
    ColorConsole
)


class TestColor:
    """Test Color enum."""

    def test_color_values(self):
        """Test that color values are correct."""
        assert Color.BLACK.value == "30"
        assert Color.RED.value == "31"
        assert Color.GREEN.value == "32"
        assert Color.YELLOW.value == "33"
        assert Color.BLUE.value == "34"
        assert Color.MAGENTA.value == "35"
        assert Color.CYAN.value == "36"
        assert Color.WHITE.value == "37"


class TestStyle:
    """Test Style enum."""

    def test_style_values(self):
        """Test that style values are correct."""
        assert Style.RESET.value == "0"
        assert Style.BOLD.value == "1"
        assert Style.DIM.value == "2"
        assert Style.ITALIC.value == "3"
        assert Style.UNDERLINE.value == "4"


class TestColorTheme:
    """Test ColorTheme dataclass."""

    def test_default_theme(self):
        """Test default theme creation."""
        theme = ColorTheme(
            name="default",
            primary=Color.BLUE,
            secondary=Color.CYAN,
            success=Color.GREEN,
            warning=Color.YELLOW,
            error=Color.RED
        )
        assert theme.name == "default"
        assert theme.primary == Color.BLUE


class TestColorFormatter:
    """Test ColorFormatter class."""

    def test_format_color(self):
        """Test color formatting."""
        formatter = ColorFormatter(enabled=True)
        formatted = formatter.format("test", color=Color.RED)
        assert "\033[31m" in formatted
        assert "test" in formatted
        assert "\033[0m" in formatted

    def test_format_style(self):
        """Test style formatting."""
        formatter = ColorFormatter(enabled=True)
        formatted = formatter.format("test", styles=[Style.BOLD])
        assert "\033[1m" in formatted
        assert "test" in formatted

    def test_format_disabled(self):
        """Test that formatting is disabled when enabled=False."""
        formatter = ColorFormatter(enabled=False)
        formatted = formatter.format("test", color=Color.RED)
        assert formatted == "test"

    def test_format_combined(self):
        """Test combined color and style formatting."""
        formatter = ColorFormatter(enabled=True)
        formatted = formatter.format("test", color=Color.RED, styles=[Style.BOLD])
        assert "\033[31m" in formatted
        assert "\033[1m" in formatted
        assert "test" in formatted


class TestColorConsole:
    """Test ColorConsole class."""

    def test_print_color(self, capsys):
        """Test printing colored text."""
        output = ColorConsole(enabled=True)
        output.print("test", color=Color.RED)
        captured = capsys.readouterr()
        assert "test" in captured.out

    def test_print_disabled(self, capsys):
        """Test printing with colors disabled."""
        output = ColorConsole(enabled=False)
        output.print("test", color=Color.RED)
        captured = capsys.readouterr()
        assert captured.out.strip() == "test"

    def test_print_multiple_args(self, capsys):
        """Test printing multiple arguments."""
        output = ColorConsole(enabled=True)
        output.print("hello", "world", color=Color.GREEN)
        captured = capsys.readouterr()
        assert "hello" in captured.out
        assert "world" in captured.out

    def test_print_to_stderr(self, capsys):
        """Test printing to stderr."""
        output = ColorConsole(enabled=True)
        output.print("error", color=Color.RED, file=sys.stderr)
        captured = capsys.readouterr()
        assert "error" in captured.err

    def test_info_method(self, capsys):
        """Test info method."""
        output = ColorConsole(enabled=True)
        output.info("info message")
        captured = capsys.readouterr()
        assert "info message" in captured.out

    def test_success_method(self, capsys):
        """Test success method."""
        output = ColorConsole(enabled=True)
        output.success("success message")
        captured = capsys.readouterr()
        assert "success message" in captured.out

    def test_warning_method(self, capsys):
        """Test warning method."""
        output = ColorConsole(enabled=True)
        output.warning("warning message")
        captured = capsys.readouterr()
        assert "warning message" in captured.out

    def test_error_method(self, capsys):
        """Test error method."""
        output = ColorConsole(enabled=True)
        output.error("error message")
        captured = capsys.readouterr()
        assert "error message" in captured.out

    def test_title_method(self, capsys):
        """Test title method."""
        output = ColorConsole(enabled=True)
        output.title("Title")
        captured = capsys.readouterr()
        assert "Title" in captured.out

    def test_subtitle_method(self, capsys):
        """Test subtitle method."""
        output = ColorConsole(enabled=True)
        output.subtitle("Subtitle")
        captured = capsys.readouterr()
        assert "Subtitle" in captured.out

    def test_separator_method(self, capsys):
        """Test separator method."""
        output = ColorConsole(enabled=True)
        output.separator(char="-", length=20)
        captured = capsys.readouterr()
        assert "-" in captured.out

    def test_bullet_method(self, capsys):
        """Test bullet method."""
        output = ColorConsole(enabled=True)
        output.bullet("item", bullet="*")
        captured = capsys.readouterr()
        assert "item" in captured.out

    def test_table_method(self, capsys):
        """Test table method."""
        output = ColorConsole(enabled=True)
        data = [
            ["Name", "Age", "City"],
            ["Alice", "30", "NYC"],
            ["Bob", "25", "LA"]
        ]
        output.table(data)
        captured = capsys.readouterr()
        assert "Alice" in captured.out
        assert "Bob" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])