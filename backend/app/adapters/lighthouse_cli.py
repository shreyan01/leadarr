"""Runs Google's Lighthouse CLI against a URL and parses the report.

Lighthouse itself only ever performs read/navigate actions against the
target (it's an auditing tool, not an attack tool), matching the
passive-only constraint the rest of the system enforces explicitly.
"""
from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from app.core.exceptions import ProviderError


def parse_lighthouse_report(raw: dict) -> dict:
    """Pure parsing function — extracts the fields DATABASE_SCHEMA.md's
    ``lighthouse_reports`` table needs. Kept separate from subprocess
    execution so it's unit-testable against a fixture."""
    categories = raw.get("categories", {})
    audits = raw.get("audits", {})

    def category_score(key: str) -> int | None:
        score = categories.get(key, {}).get("score")
        return round(score * 100) if score is not None else None

    def audit_numeric(key: str) -> float | None:
        value = audits.get(key, {}).get("numericValue")
        return round(value, 2) if value is not None else None

    return {
        "performance_score": category_score("performance"),
        "accessibility_score": category_score("accessibility"),
        "seo_score": category_score("seo"),
        "best_practices_score": category_score("best-practices"),
        "lcp_ms": audit_numeric("largest-contentful-paint"),
        "cls": audit_numeric("cumulative-layout-shift"),
        "speed_index_ms": audit_numeric("speed-index"),
        "tti_ms": audit_numeric("interactive"),
        "fcp_ms": audit_numeric("first-contentful-paint"),
    }


class LighthouseCliAdapter:
    def __init__(self, cli_path: str, timeout_s: float = 90.0) -> None:
        self._cli_path = cli_path
        self._timeout_s = timeout_s

    async def run(self, url: str) -> dict:
        """Runs Lighthouse headlessly and returns the raw report JSON."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "report.json"
            cmd = [
                self._cli_path,
                url,
                "--output=json",
                f"--output-path={output_path}",
                "--chrome-flags=--headless=new --no-sandbox",
                "--quiet",
            ]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            try:
                _, stderr = await asyncio.wait_for(process.communicate(), timeout=self._timeout_s)
            except asyncio.TimeoutError as exc:
                process.kill()
                raise ProviderError(f"Lighthouse timed out after {self._timeout_s}s for {url}") from exc

            if process.returncode != 0 or not output_path.exists():
                raise ProviderError(f"Lighthouse failed for {url}: {stderr.decode(errors='replace')[:500]}")

            return json.loads(output_path.read_text())
