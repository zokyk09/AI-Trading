from backend.trading.risk_manager import validate_order


def test_live_mode_is_rejected():
    accepted, _ = validate_order(mode="live", risk_percent=0.5, volume=0.01)
    assert not accepted


def test_risk_above_limit_is_rejected():
    accepted, _ = validate_order(mode="demo", risk_percent=2, volume=0.01)
    assert not accepted


def test_volume_above_demo_limit_is_rejected():
    accepted, _ = validate_order(mode="demo", risk_percent=0.5, volume=0.02)
    assert not accepted
