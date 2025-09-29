import os
import csv
from apps.agents import name_resolver


def write_aliases(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        writer = csv.writer(f)
        for r in rows:
            writer.writerow(r)


def test_exact_and_alias(tmp_path, monkeypatch):
    csv_path = tmp_path / "aliases.csv"
    rows = [["Christian McCaffrey", "CMC", "Christian M."], ["Justin Jefferson", "JJeff"]]
    write_aliases(str(csv_path), rows)
    monkeypatch.setenv("ALIASES_CSV_PATH", str(csv_path))

    res = name_resolver.resolve("Christian McCaffrey")
    assert res["name"] == "Christian McCaffrey"
    assert res["score"] == 100.0

    res2 = name_resolver.resolve("CMC")
    assert res2["name"] == "Christian McCaffrey"
    assert res2["score"] == 100.0


def test_typo_and_low_confidence(tmp_path, monkeypatch):
    csv_path = tmp_path / "aliases.csv"
    rows = [["Christian McCaffrey", "CMC"] , ["Justin Jefferson", "JJeff"]]
    write_aliases(str(csv_path), rows)
    monkeypatch.setenv("ALIASES_CSV_PATH", str(csv_path))

    # Typo: 'Christan McCafrey' -> expect fuzzy or fallback with decent score
    res = name_resolver.resolve("Christan McCafrey")
    assert res["name"] is not None
    # if rapidfuzz not installed, we expect fallback low confidence or decent SequenceMatcher
    assert "score" in res

    # Low confidence nonsensical input
    res2 = name_resolver.resolve("Xyzabc")
    assert res2["warning"] == "low_confidence"
