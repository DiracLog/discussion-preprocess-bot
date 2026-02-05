import pytest
from DiscordBot import create_session_report_embed

# mock data
SAMPLE_ANALYSIS = {
    "reviews": [
        {
            "title": "Discussion about Docker",
            "mark": 9,
            "sentiment": "positive",
            "arguments": ["Docker is useful"]
        }
    ]
}

def test_report_generation_title():
    members = ["UserA", "UserB"]
    embed = create_session_report_embed(SAMPLE_ANALYSIS, members, "12345")
    assert "Club Meeting Report" in embed.title
    assert embed.color.value == 3447003 

def test_report_participants():
    members = ["Alice", "Bob"]
    embed = create_session_report_embed(SAMPLE_ANALYSIS, members, "123")
    assert "Alice, Bob" in embed.description

def test_empty_analysis():
    empty_data = {"reviews": []}
    embed = create_session_report_embed(empty_data, [], "000")
    assert embed.title == "⚠️ Analysis Empty"