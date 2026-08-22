"""Tests for TikTok Stealth Human Simulation and Cookie Health Check."""

import time
from connectors.tiktok.human_simulator import (
    generate_bezier_curve,
    check_cookie_health,
)


def test_bezier_curve_generation():
    """Verify Bézier curve creates smooth interpolated points between start and end."""
    start = (100.0, 100.0)
    end = (500.0, 400.0)
    steps = 20

    points = generate_bezier_curve(start, end, steps=steps)

    assert len(points) == steps + 1
    # Start and End points should match approximately (within micro-jitter)
    assert abs(points[0][0] - start[0]) < 0.1
    assert abs(points[0][1] - start[1]) < 0.1
    assert abs(points[-1][0] - end[0]) < 0.1
    assert abs(points[-1][1] - end[1]) < 0.1

    # Short distance edge case
    short_points = generate_bezier_curve((10.0, 10.0), (12.0, 11.0), steps=10)
    assert len(short_points) == 2


def test_cookie_health_check_valid():
    """Test cookie health returns valid when sessionid is present and unexpired."""
    future_time = time.time() + 86400 * 30  # 30 days in future
    cookies = [
        {"name": "sessionid", "value": "abc123xyz", "expirationDate": future_time},
        {"name": "tt_csrf_token", "value": "token123", "expirationDate": future_time},
    ]

    res = check_cookie_health(cookies)
    assert res["valid"] is True
    assert res["expires_in_days"] >= 29


def test_cookie_health_check_expired():
    """Test cookie health returns invalid when sessionid is expired."""
    past_time = time.time() - 3600  # 1 hour ago
    cookies = [
        {"name": "sessionid", "value": "abc123xyz", "expirationDate": past_time},
    ]

    res = check_cookie_health(cookies)
    assert res["valid"] is False
    assert "hết hạn" in res["reason"]


def test_cookie_health_check_missing_sessionid():
    """Test cookie health returns invalid when sessionid cookie is missing."""
    cookies = [
        {"name": "tt_csrf_token", "value": "token123", "expirationDate": time.time() + 86400},
    ]

    res = check_cookie_health(cookies)
    assert res["valid"] is False
    assert "Thiếu cookie" in res["reason"]
