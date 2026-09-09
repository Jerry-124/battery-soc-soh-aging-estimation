from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    spec = spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUN_EXPERIMENT = _load_script("run_experiment")
RUN_CX2 = _load_script("run_cx2_pulse_aging")


def test_all_experiment_artifacts_live_under_requested_output_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "run-a"

    metrics_dir, figures_dir, data_dir = RUN_EXPERIMENT.output_directories(root)

    assert metrics_dir == root / "metrics"
    assert figures_dir == root / "figures"
    assert data_dir == root / "data" / "processed"
    assert all(
        path.is_relative_to(root) for path in (metrics_dir, figures_dir, data_dir)
    )


def test_two_output_roots_do_not_share_processed_dataset_paths(tmp_path: Path) -> None:
    root_a = tmp_path / "run-a"
    root_b = tmp_path / "run-b"

    dirs_a = set(RUN_EXPERIMENT.output_directories(root_a))
    dirs_b = set(RUN_EXPERIMENT.output_directories(root_b))

    assert dirs_a.isdisjoint(dirs_b)
    assert root_a / "data" / "processed" in dirs_a
    assert root_b / "data" / "processed" in dirs_b


def test_cx2_custom_output_root_isolates_processed_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "cx2-run"

    directories = RUN_CX2.output_directories(root)

    assert directories["metrics"] == root / "metrics"
    assert directories["figures"] == root / "figures"
    assert directories["reports"] == root / "reports"
    assert directories["processed"] == root / "data" / "processed"
    assert all(path.is_relative_to(root) for path in directories.values())
