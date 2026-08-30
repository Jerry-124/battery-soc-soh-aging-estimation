from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = spec_from_file_location("run_experiment", ROOT / "scripts" / "run_experiment.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
output_directories = MODULE.output_directories


def test_all_experiment_artifacts_live_under_requested_output_root(tmp_path: Path) -> None:
    root = tmp_path / "run-a"

    metrics_dir, figures_dir, data_dir = output_directories(root)

    assert metrics_dir == root / "metrics"
    assert figures_dir == root / "figures"
    assert data_dir == root / "data" / "processed"
    assert all(path.is_relative_to(root) for path in (metrics_dir, figures_dir, data_dir))


def test_two_output_roots_do_not_share_processed_dataset_paths(tmp_path: Path) -> None:
    root_a = tmp_path / "run-a"
    root_b = tmp_path / "run-b"

    dirs_a = set(output_directories(root_a))
    dirs_b = set(output_directories(root_b))

    assert dirs_a.isdisjoint(dirs_b)
    assert root_a / "data" / "processed" in dirs_a
    assert root_b / "data" / "processed" in dirs_b
