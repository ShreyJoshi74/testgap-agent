"""Unit tests for score_gap and priority_label pure functions (Task 2.5)."""

from __future__ import annotations

from testgap.find_gaps import priority_label, score_gap


class TestScoreGap:
    def test_public_9_missing_in_readme(self):
        # 9 × 2 + 10 = 28
        assert score_gap(9, is_public=True, in_docs=True) == 28

    def test_private_3_missing_not_in_docs(self):
        # 3 × 1 + 0 = 3
        assert score_gap(3, is_public=False, in_docs=False) == 3

    def test_public_5_missing_in_readme(self):
        # 5 × 2 + 10 = 20  (boundary: exactly high)
        assert score_gap(5, is_public=True, in_docs=True) == 20

    def test_public_4_missing_in_readme(self):
        # 4 × 2 + 10 = 18  (boundary: medium)
        assert score_gap(4, is_public=True, in_docs=True) == 18

    def test_public_4_missing_not_in_docs(self):
        # 4 × 2 + 0 = 8  (boundary: exactly medium)
        assert score_gap(4, is_public=True, in_docs=False) == 8

    def test_private_7_missing_not_in_docs(self):
        # 7 × 1 + 0 = 7  (boundary: low)
        assert score_gap(7, is_public=False, in_docs=False) == 7

    def test_zero_missing(self):
        assert score_gap(0, is_public=True, in_docs=True) == 10

    def test_private_in_docs(self):
        # 2 × 1 + 10 = 12
        assert score_gap(2, is_public=False, in_docs=True) == 12


class TestPriorityLabel:
    def test_high_at_28(self):
        assert priority_label(28) == "high"

    def test_high_at_20_boundary(self):
        # boundary: exactly 20 → high
        assert priority_label(20) == "high"

    def test_medium_at_18_boundary(self):
        # 18 < 20 → medium
        assert priority_label(18) == "medium"

    def test_medium_at_8_boundary(self):
        # exactly 8 → medium
        assert priority_label(8) == "medium"

    def test_low_at_7_boundary(self):
        # 7 < 8 → low
        assert priority_label(7) == "low"

    def test_low_at_3(self):
        assert priority_label(3) == "low"

    def test_low_at_0(self):
        assert priority_label(0) == "low"

    def test_public_9_in_readme_is_high(self):
        # From score_gap test: score=28 → high
        assert priority_label(score_gap(9, is_public=True, in_docs=True)) == "high"

    def test_private_3_not_in_docs_is_low(self):
        assert priority_label(score_gap(3, is_public=False, in_docs=False)) == "low"

    def test_public_5_in_readme_is_high(self):
        # score=20 → high
        assert priority_label(score_gap(5, is_public=True, in_docs=True)) == "high"

    def test_public_4_in_readme_is_medium(self):
        # score=18 → medium
        assert priority_label(score_gap(4, is_public=True, in_docs=True)) == "medium"

    def test_public_4_not_in_docs_is_medium(self):
        # score=8 → medium
        assert priority_label(score_gap(4, is_public=True, in_docs=False)) == "medium"

    def test_private_7_not_in_docs_is_low(self):
        # score=7 → low
        assert priority_label(score_gap(7, is_public=False, in_docs=False)) == "low"


class TestIsPublicViaScoring:
    """Verify __init__ (dunder) counts as public via the scorer."""

    def test_dunder_init_counts_as_public(self):
        from testgap.find_gaps import _is_public
        assert _is_public("__init__") is True

    def test_dunder_eq_counts_as_public(self):
        from testgap.find_gaps import _is_public
        assert _is_public("__eq__") is True

    def test_underscore_helper_is_private(self):
        from testgap.find_gaps import _is_public
        assert _is_public("_helper") is False

    def test_class_method_dunder(self):
        from testgap.find_gaps import _is_public
        assert _is_public("MyClass.__init__") is True


class TestWholeWordDocMatch:
    """Whole-word matching: 'total' must NOT match 'calculate_total'."""

    def test_short_name_not_found_in_longer_word(self, tmp_path):
        from testgap.find_gaps import _mentioned_in_docs
        readme = tmp_path / "README.md"
        readme.write_text("Use calculate_total to sum items.", encoding="utf-8")
        # "total" is not a whole-word match inside "calculate_total"
        assert _mentioned_in_docs("total", tmp_path) is False

    def test_exact_name_is_found(self, tmp_path):
        from testgap.find_gaps import _mentioned_in_docs
        readme = tmp_path / "README.md"
        readme.write_text("Use calculate_total to sum items.", encoding="utf-8")
        assert _mentioned_in_docs("calculate_total", tmp_path) is True

    def test_method_name_matched_by_leaf(self, tmp_path):
        from testgap.find_gaps import _mentioned_in_docs
        readme = tmp_path / "README.md"
        readme.write_text("Call method_one for results.", encoding="utf-8")
        # "MyClass.method_one" → matches on "method_one"
        assert _mentioned_in_docs("MyClass.method_one", tmp_path) is True

    def test_no_readme_returns_false(self, tmp_path):
        from testgap.find_gaps import _mentioned_in_docs
        assert _mentioned_in_docs("calculate_total", tmp_path) is False
