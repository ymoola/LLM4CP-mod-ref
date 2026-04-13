from __future__ import annotations

from typing import Any


def _line_range_schema() -> dict[str, Any]:
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {'start': {'type': 'integer'}, 'end': {'type': 'integer'}},
        'required': ['start', 'end'],
    }


def parser_schema() -> dict[str, Any]:
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'mappings': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'nl_snippet': {'type': 'string'},
                        'model_lines': _line_range_schema(),
                        'code_excerpt': {'type': 'string'},
                        'variables': {'type': 'array', 'items': {'type': 'string'}},
                        'reasoning': {'type': 'string'},
                        'confidence': {'type': 'number'},
                    },
                    'required': ['nl_snippet', 'model_lines', 'code_excerpt', 'variables', 'reasoning', 'confidence'],
                },
            },
            'unmapped_nl': {'type': 'array', 'items': {'type': 'string'}},
            'unmapped_model_segments': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'model_lines': _line_range_schema(),
                        'code_excerpt': {'type': 'string'},
                        'reasoning': {'type': 'string'},
                    },
                    'required': ['model_lines', 'code_excerpt', 'reasoning'],
                },
            },
        },
        'required': ['mappings', 'unmapped_nl', 'unmapped_model_segments'],
    }


def clarification_assessor_schema() -> dict[str, Any]:
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'status': {'type': 'string', 'enum': ['proceed', 'needs_clarification']},
            'reason': {'type': 'string'},
            'questions': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 3},
            'clarified_request_summary': {'type': 'string'},
        },
        'required': ['status', 'reason', 'questions', 'clarified_request_summary'],
    }


def planner_schema() -> dict[str, Any]:
    line_range = _line_range_schema()
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'plan': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'change_type': {'type': 'string'},
                        'title': {'type': 'string'},
                        'description': {'type': 'string'},
                        'target_lines': {'anyOf': [line_range, {'type': 'null'}]},
                        'insert_after_line': {'type': ['integer', 'null']},
                        'strategy': {'type': 'string'},
                        'confidence': {'type': ['number', 'null']},
                        'risks': {'type': 'string'},
                    },
                    'required': ['change_type', 'title', 'description', 'target_lines', 'insert_after_line', 'strategy', 'confidence', 'risks'],
                },
            },
            'preserve_sections': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'model_lines': line_range,
                        'reason': {'type': 'string'},
                    },
                    'required': ['model_lines', 'reason'],
                },
            },
            'notes_for_modifier': {'type': 'string'},
        },
        'required': ['plan', 'preserve_sections', 'notes_for_modifier'],
    }


def planner_validator_schema() -> dict[str, Any]:
    line_range = _line_range_schema()
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'status': {'type': 'string', 'enum': ['pass', 'needs_changes']},
            'summary': {'type': 'string'},
            'issues': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'title': {'type': 'string'},
                        'description': {'type': 'string'},
                        'category': {'type': 'string'},
                        'severity': {'type': 'string', 'enum': ['high', 'medium', 'low']},
                        'target_lines': {'anyOf': [line_range, {'type': 'null'}]},
                        'suggestion': {'type': 'string'},
                    },
                    'required': ['title', 'description', 'category', 'severity', 'target_lines', 'suggestion'],
                },
            },
            'notes_for_planner': {'type': 'string'},
        },
        'required': ['status', 'summary', 'issues', 'notes_for_planner'],
    }


def validator_schema() -> dict[str, Any]:
    line_range = _line_range_schema()
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'status': {'type': 'string', 'enum': ['pass', 'needs_changes']},
            'summary': {'type': 'string'},
            'issues': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'title': {'type': 'string'},
                        'description': {'type': 'string'},
                        'category': {'type': 'string'},
                        'severity': {'type': 'string', 'enum': ['high', 'medium', 'low']},
                        'generated_lines': {'anyOf': [line_range, {'type': 'null'}]},
                        'reference_lines': {'anyOf': [line_range, {'type': 'null'}]},
                        'suggestion': {'type': 'string'},
                    },
                    'required': ['title', 'description', 'category', 'severity', 'generated_lines', 'reference_lines', 'suggestion'],
                },
            },
            'invariants': {
                'type': 'object',
                'additionalProperties': False,
                'properties': {
                    'variables_preserved': {'type': 'array', 'items': {'type': 'string'}},
                    'variables_added': {'type': 'array', 'items': {'type': 'string'}},
                    'objective_changed': {'type': 'boolean'},
                    'constraints_added': {'type': 'array', 'items': {'type': 'string'}},
                    'constraints_modified': {'type': 'array', 'items': {'type': 'string'}},
                    'constraints_removed': {'type': 'array', 'items': {'type': 'string'}},
                },
                'required': ['variables_preserved', 'variables_added', 'objective_changed', 'constraints_added', 'constraints_modified', 'constraints_removed'],
            },
            'change_summary': {'type': 'string'},
            'notes_for_modifier': {'type': 'string'},
        },
        'required': ['status', 'summary', 'issues', 'invariants', 'change_summary', 'notes_for_modifier'],
    }
