from app.core import MAX_FILES, build_roast_prompt, parse_score, select_files


def test_select_files_prioritizes_docs_manifests_entrypoints_and_large_source():
    tree = [
        {"type": "blob", "path": "src/tiny.py", "size": 10},
        {"type": "blob", "path": "src/large.py", "size": 5000},
        {"type": "blob", "path": "README.md", "size": 100},
        {"type": "blob", "path": "pyproject.toml", "size": 200},
        {"type": "blob", "path": "src/main.py", "size": 300},
        {"type": "blob", "path": "assets/logo.png", "size": 9000},
        {"type": "tree", "path": "src"},
    ]
    paths = [item["path"] for item in select_files(tree)]
    assert paths[:3] == ["README.md", "pyproject.toml", "src/main.py"]
    assert paths[3:] == ["src/large.py", "src/tiny.py"]
    assert "assets/logo.png" not in paths


def test_select_files_caps_count():
    tree = [{"type": "blob", "path": f"src/file{i}.py", "size": i} for i in range(30)]
    assert len(select_files(tree)) == MAX_FILES


def test_prompt_is_bounded_and_names_files():
    prompt = build_roast_prompt("owner/repo", [("a.py", "x" * 30_000), ("b.py", "print('b')")])
    assert len(prompt) <= 24_000
    assert "owner/repo" in prompt
    assert "--- a.py ---" in prompt
    assert "SCORE: n/10" in prompt


def test_score_is_read_from_required_last_line():
    assert parse_score("Good grief.\nSCORE: 7/10") == 7
    assert parse_score("No score") is None

