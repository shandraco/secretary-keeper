from app.diff import diff_clauses
from app.documents import find_refs, parse_policy, split_clauses, terms_defined

PATTERN = r"[A-Z]{2,6}-\d{1,5}"


def test_split_clauses_numbers_headings_and_bodies():
    clauses = split_clauses("# Title\n\n## 4 Lockout devices\n4.1 Each worker gets a lock.\n4.2 Devices are inspected weekly.\n")
    by = {c.number: c for c in clauses}
    assert by["4"].heading == "Lockout devices"
    assert by["4.2"].body == "Devices are inspected weekly."
    assert by["0"].body == "Title"


def test_list_items_stay_inside_their_clause():
    clauses = split_clauses("4.2 Inspect devices as follows:\n1. Check the lock.\n2. Check the tag.\n")
    assert [c.number for c in clauses] == ["4.2"]
    assert "Check the tag." in clauses[0].body


def test_duplicate_numbers_are_kept_apart():
    numbers = [c.number for c in split_clauses("1.1 First.\n1.1 Second.\n")]
    assert numbers == ["1.1", "1.1~2"]


def test_find_refs_section_and_whole_policy():
    assert find_refs("as required by POL-007 §4.2", PATTERN) == [("POL-007", "4.2")]
    assert find_refs("see §5 of POL-007 and POL-009", PATTERN) == [("POL-007", "5"), ("POL-009", None)]
    assert find_refs("this policy, POL-007 section 3", PATTERN, own_id="POL-007") == []


def test_terms_defined():
    assert terms_defined('2.1 "Isolation point" means a valve.') == ["Isolation point"]
    assert terms_defined("**Authorized worker** refers to someone trained.") == ["Authorized worker"]


def test_parse_policy_reads_front_matter(samples):
    doc = parse_policy("SAF-112.md", (samples / "policies" / "SAF-112.md").read_bytes(), PATTERN)
    assert (doc.id, doc.title, doc.parent, doc.subsets, doc.version) == ("SAF-112", "Maintenance Access", "POL-007", ["Safety"], 1)


def test_diff_finds_modified_added_removed_and_renumbered():
    old = split_clauses("1.1 Keep this.\n1.2 Change this weekly.\n1.3 Remove this.\n1.4 This sentence moves to a new number.\n")
    new = split_clauses("1.1 Keep this.\n1.2 Change this daily.\n1.5 This sentence moves to a new number.\n1.6 Brand new rule.\n")
    kinds = {(c.number, c.kind) for c in diff_clauses(old, new)}
    assert kinds == {("1.2", "modified"), ("1.3", "removed"), ("1.5", "renumbered"), ("1.6", "added")}


def test_diff_of_samples(samples):
    old = parse_policy("a.md", (samples / "policies" / "POL-007.md").read_bytes(), PATTERN)
    new = parse_policy("b.md", (samples / "changes" / "POL-007-v4.md").read_bytes(), PATTERN)
    changes = {c.number: c for c in diff_clauses(old.clauses, new.clauses)}
    assert set(changes) == {"2.1", "2.2", "4.2", "5.3"}
    assert changes["2.1"].terms == ["Isolation point"]
    assert changes["5.3"].kind == "added"
