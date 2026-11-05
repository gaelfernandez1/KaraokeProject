from karaoke_server.config import Settings
from karaoke_server.doctor import network_checks, render
from karaoke_server.network import NetworkState


def test_doctor_reports_nat_mode_with_a_fix(settings: Settings) -> None:
    checks = network_checks(settings, NetworkState("nat", "192.168.1.43", None, None))
    home = next(c for c in checks if c.name == "home network")
    assert not home.ok
    assert "networkingMode=mirrored" in home.fix


def test_doctor_warns_when_tailscale_points_at_the_home_port(settings: Settings) -> None:
    checks = network_checks(settings, NetworkState("mirrored", "192.168.1.43", "g.ts.net", 8765))
    remote = next(c for c in checks if c.name == "outside home")
    assert not remote.ok
    assert "8766" in remote.fix
    good = network_checks(settings, NetworkState("mirrored", "192.168.1.43", "g.ts.net", 8766))
    assert next(c for c in good if c.name == "outside home").ok


def test_render_marks_each_check(settings: Settings) -> None:
    text = render(network_checks(settings, NetworkState("mirrored", "192.168.1.43", None, None)))
    assert "✓ home network" in text
    assert "· outside home" in text
