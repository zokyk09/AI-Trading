from backend.ai.strategy import decide

def test_strategy_defaults_to_hold():
    assert decide({}) == "HOLD"
