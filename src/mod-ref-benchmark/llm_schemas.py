from __future__ import annotations

from typing import Any


def _line_range_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "start": {"type": "integer"},
            "end": {"type": "integer"},
        },
        "required": ["start", "end"],
    }


def build_parser_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "mappings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "nl_snippet": {"type": "string"},
                        "model_lines": _line_range_schema(),
                        "code_excerpt": {"type": "string"},
                        "variables": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "reasoning": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": [
                        "nl_snippet",
                        "model_lines",
                        "code_excerpt",
                        "variables",
                        "reasoning",
                        "confidence",
                    ],
                },
            },
            "unmapped_nl": {
                "type": "array",
                "items": {"type": "string"},
            },
            "unmapped_model_segments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "model_lines": _line_range_schema(),
                        "code_excerpt": {"type": "string"},
                        "reasoning": {"type": "string"},
                    },
                    "required": ["model_lines", "code_excerpt", "reasoning"],
                },
            },
        },
        "required": ["mappings", "unmapped_nl", "unmapped_model_segments"],
    }


def build_planner_schema() -> dict[str, Any]:
    line_range_schema = _line_range_schema()
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "plan": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "change_type": {
                            "type": "string",
                            "enum": [
                                "add_constraint",
                                "modify_constraint",
                                "remove_constraint",
                                "add_objective",
                                "modify_objective",
                                "data_handling",
                                "other",
                            ],
                        },
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "related_nl": {"type": "string"},
                        "target_lines": {
                            "anyOf": [line_range_schema, {"type": "null"}],
                        },
                        "insert_after_line": {"type": ["integer", "null"]},
                        "code_excerpt": {"type": "string"},
                        "strategy": {"type": "string"},
                        "confidence": {"type": ["number", "null"]},
                        "risks": {"type": "string"},
                    },
                    "required": [
                        "change_type",
                        "title",
                        "description",
                        "related_nl",
                        "target_lines",
                        "insert_after_line",
                        "code_excerpt",
                        "strategy",
                        "confidence",
                        "risks",
                    ],
                },
            },
            "preserve_sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "model_lines": line_range_schema,
                        "reason": {"type": "string"},
                    },
                    "required": ["model_lines", "reason"],
                },
            },
            "notes_for_modifier": {"type": "string"},
        },
        "required": ["plan", "preserve_sections", "notes_for_modifier"],
    }


def build_planner_validator_schema() -> dict[str, Any]:
    line_range_schema = _line_range_schema()
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "status": {"type": "string", "enum": ["pass", "needs_changes"]},
            "summary": {"type": "string"},
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "category": {
                            "type": "string",
                            "enum": [
                                "missing_change",
                                "incorrect_target",
                                "unnecessary_change",
                                "preservation_risk",
                                "line_reference",
                                "other",
                            ],
                        },
                        "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                        "target_lines": {"anyOf": [line_range_schema, {"type": "null"}]},
                        "suggestion": {"type": "string"},
                        "confidence": {"type": ["number", "null"]},
                    },
                    "required": [
                        "title",
                        "description",
                        "category",
                        "severity",
                        "target_lines",
                        "suggestion",
                        "confidence",
                    ],
                },
            },
            "notes_for_planner": {"type": "string"},
        },
        "required": ["status", "summary", "issues", "notes_for_planner"],
    }


def build_validator_schema() -> dict[str, Any]:
    line_range_schema = _line_range_schema()
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "status": {"type": "string", "enum": ["pass", "needs_changes"]},
            "summary": {"type": "string"},
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "category": {
                            "type": "string",
                            "enum": [
                                "missing_constraint",
                                "incorrect_constraint",
                                "objective",
                                "data_handling",
                                "output_format",
                                "style",
                                "other",
                            ],
                        },
                        "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                        "generated_lines": {
                            "anyOf": [line_range_schema, {"type": "null"}],
                        },
                        "reference_lines": {
                            "anyOf": [line_range_schema, {"type": "null"}],
                        },
                        "suggestion": {"type": "string"},
                        "confidence": {"type": ["number", "null"]},
                    },
                    "required": [
                        "title",
                        "description",
                        "category",
                        "severity",
                        "generated_lines",
                        "reference_lines",
                        "suggestion",
                        "confidence",
                    ],
                },
            },
            "notes_for_modifier": {"type": "string"},
        },
        "required": ["status", "summary", "issues", "notes_for_modifier"],
    }


def build_code_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "python_code": {
                "type": "string",
                "description": "A complete Python script (CPMPy) that reads input_data.json, solves the CR, and prints JSON.",
            }
        },
        "required": ["python_code"],
    }
