from pathlib import Path

import duckdb

from ga4_platform.config import Settings
from ga4_platform.pipeline import build
from ga4_platform.quality import run


def fixture_settings(tmp_path: Path) -> Settings:
    root = Path(__file__).resolve().parents[1]
    return Settings(root, root / "data/fixtures/events_fixture.csv", tmp_path / "ga4.duckdb", True)


def test_fixture_pipeline_builds_layers(tmp_path):
    settings = fixture_settings(tmp_path)
    result = build(settings)
    assert result == {"mode": "fixture", "events": 20, "users": 5, "days": 5, "orders": 2, "revenue": 144.5}
    con = duckdb.connect(str(settings.database), read_only=True)
    assert con.execute("select count(*) from ads.funnel").fetchone()[0] == 5
    assert con.execute("select max(users)-min(users) from ads.funnel").fetchone()[0] >= 0


def test_fixture_quality_passes(tmp_path):
    settings = fixture_settings(tmp_path)
    build(settings)
    report = run(settings)
    assert report["mode"] == "fixture"
    assert report["rules"] == 12
    assert report["failed"] == 0


def test_platform_contract_exports(tmp_path):
    settings = fixture_settings(tmp_path)
    build(settings)
    assert (settings.root / "data/platform/ga4_events.parquet").exists()

