import inspect

import pytest

from app.agents.vyapar_sathi_agent import VyaparSathiAgent


def test_parse_plain_valid_json():
    action = VyaparSathiAgent.parse_action_json(
        '{"action":"call_tool","tool_name":"query_transactions","tool_input":{"query":"total expenses this month"}}'
    )
    assert action.action == "call_tool"
    assert action.tool_name == "query_transactions"


def test_parse_fenced_json():
    action = VyaparSathiAgent.parse_action_json(
        '```json\n{"action":"final_answer","final_answer":"Hello"}\n```'
    )
    assert action.action == "final_answer"
    assert action.final_answer == "Hello"


def test_extract_json_from_surrounding_text():
    action = VyaparSathiAgent.parse_action_json(
        'Sure, here is the result:\n{"action":"final_answer","final_answer":"Done"}\nThanks.'
    )
    assert action.final_answer == "Done"


def test_reject_malformed_json():
    with pytest.raises(Exception):
        VyaparSathiAgent.parse_action_json('{"action":"call_tool",')


def test_reject_unknown_tool():
    with pytest.raises(Exception):
        VyaparSathiAgent.parse_action_json(
            '{"action":"call_tool","tool_name":"drop_database","tool_input":{}}'
        )


def test_reject_call_tool_without_tool_name():
    with pytest.raises(Exception):
        VyaparSathiAgent.parse_action_json('{"action":"call_tool","tool_input":{}}')


def test_reject_final_answer_without_text():
    with pytest.raises(Exception):
        VyaparSathiAgent.parse_action_json('{"action":"final_answer"}')


def test_parser_does_not_use_eval():
    source = inspect.getsource(VyaparSathiAgent.parse_action_json)
    assert "eval(" not in source
