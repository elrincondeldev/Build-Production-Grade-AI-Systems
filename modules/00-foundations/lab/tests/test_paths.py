from kestrel_foundations.paths import data_dir, handbook_dir, repo_root


def test_repo_root_contains_datasets():
    root = repo_root()
    assert (root / "datasets" / "fraud" / "generate.py").exists()


def test_data_dir_override(monkeypatch, tmp_path):
    monkeypatch.setenv("KESTREL_DATA_DIR", str(tmp_path))
    assert data_dir() == tmp_path.resolve()


def test_handbook_has_documents():
    assert len(list(handbook_dir().glob("*.md"))) >= 10
