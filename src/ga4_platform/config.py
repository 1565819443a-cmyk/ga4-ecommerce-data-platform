from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    root: Path
    source_file: Path
    database: Path
    fixture_mode: bool = False

    @classmethod
    def load(cls, root: Path | None = None, fixture_mode: bool = False) -> "Settings":
        base = (root or Path(__file__).resolve().parents[2]).resolve()
        source = base / ("data/fixtures/events_fixture.csv" if fixture_mode else os.getenv("GA4_EXPORT_URI", "data/raw/ga4_events.parquet"))
        return cls(base, source, base / "data/processed/ga4.duckdb", fixture_mode)

