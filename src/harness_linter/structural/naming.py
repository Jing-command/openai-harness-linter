"""Naming convention structural checks."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from harness_linter.structural.base import StructuralCheck, StructuralViolation


@dataclass
class LayerNamingRules:
    """层的命名规则"""
    class_suffixes: list[str] = field(default_factory=list)
    function_prefixes: list[str] = field(default_factory=list)


@dataclass
class NamingConfig:
    """命名约定配置"""
    layer_patterns: dict[str, LayerNamingRules] = field(default_factory=dict)


class NamingCheck(StructuralCheck):
    """检查命名约定"""

    def __init__(self, config: NamingConfig | None = None):
        super().__init__("naming")
        self.config = config or self._default_config()

    def _default_config(self) -> NamingConfig:
        """Create default naming configuration.

        Default configuration:
        - service layer: class names end with Service
        - repo layer: class names end with Repository or Repo
        """
        return NamingConfig(
            layer_patterns={
                "service": LayerNamingRules(
                    class_suffixes=["Service"],
                ),
                "repo": LayerNamingRules(
                    class_suffixes=["Repository", "Repo"],
                ),
            }
        )

    def check_file(self, file_path: Path, **context) -> list[StructuralViolation]:
        """Check file for naming convention violations.

        Args:
            file_path: Path to the file to check
            **context: Additional context, may include 'layer' key

        Returns:
            List of structural violations found
        """
        violations: list[StructuralViolation] = []

        # Get layer from context
        layer = context.get("layer")
        if not layer:
            return violations

        # Check if we have rules for this layer
        if layer not in self.config.layer_patterns:
            return violations

        rules = self.config.layer_patterns[layer]

        # Parse the file
        try:
            content = file_path.read_text(encoding="utf-8")
            if not content.strip():
                return violations

            tree = ast.parse(content)
        except (IOError, UnicodeDecodeError) as e:
            violations.append(
                StructuralViolation(
                    check_name=self.name,
                    message=f"Could not read file: {e}",
                    file_path=file_path,
                    suggestion="Check file permissions and encoding",
                )
            )
            return violations
        except SyntaxError as e:
            violations.append(
                StructuralViolation(
                    check_name=self.name,
                    message=f"Syntax error in file: {e}",
                    file_path=file_path,
                    line_number=e.lineno,
                    suggestion="Fix the syntax error before running naming checks",
                )
            )
            return violations

        # Find all class definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                line_number = node.lineno

                # Check class name against suffix rules
                if rules.class_suffixes:
                    if not any(class_name.endswith(suffix) for suffix in rules.class_suffixes):
                        expected = " or ".join(f"*{suffix}" for suffix in rules.class_suffixes)
                        violations.append(
                            StructuralViolation(
                                check_name=self.name,
                                message=f"Class '{class_name}' in {layer} layer does not follow naming convention",
                                file_path=file_path,
                                line_number=line_number,
                                suggestion=f"Consider renaming to {expected}",
                            )
                        )

        return violations
