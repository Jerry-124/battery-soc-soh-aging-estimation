from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_public_report_generators_keep_structured_markdown_contract() -> None:
    scripts = (
        "generate_report.py",
        "run_calce_validation.py",
        "run_oxford_soh_validation.py",
        "run_cx2_pulse_aging.py",
        "run_aging_aware_comparison.py",
        "run_robustness_matrix.py",
    )
    for name in scripts:
        source = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert "## Scope" in source, name
        assert "## Key Results" in source, name
        assert "## Interpretation" in source, name

    robustness_source = (ROOT / "scripts" / "run_robustness_matrix.py").read_text(
        encoding="utf-8"
    )
    assert '"```json"' not in robustness_source

    synthetic_source = (ROOT / "scripts" / "generate_report.py").read_text(
        encoding="utf-8"
    )
    assert "First Within ±2 %pt" in synthetic_source
    assert "METHOD_LABELS" in synthetic_source
