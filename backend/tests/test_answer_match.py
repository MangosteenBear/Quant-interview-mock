"""
答案匹配单元测试
运行：pytest tests/test_answer_match.py -v
"""
import pytest
from app.utils.answer_match import (
    normalize_text,
    to_number,
    expand_alternatives,
    blank_match,
    judge_choice,
    judge_fill,
    format_fill_answer,
)


# ─── normalize_text ──────────────────────────────────────────────────────────

class TestNormalizeText:
    def test_strips_whitespace(self):
        assert normalize_text("  answer  ") == "answer"

    def test_numbered_prefix(self):
        assert normalize_text("1. delta") == "delta"
        assert normalize_text("2) sigma") == "sigma"
        assert normalize_text("3、gamma") == "gamma"

    def test_circled_prefix(self):
        assert normalize_text("① answer") == "answer"
        assert normalize_text("⑤ result") == "result"

    def test_latex_wrapper(self):
        assert normalize_text("$\\delta$") == "\\delta"
        assert normalize_text("$0.5$") == "0.5"

    def test_trailing_punctuation(self):
        assert normalize_text("answer.") == "answer"
        assert normalize_text("answer,") == "answer"
        assert normalize_text("答案。") == "答案"

    def test_lowercase(self):
        assert normalize_text("Delta") == "delta"
        assert normalize_text("BLACK-SCHOLES") == "black-scholes"

    def test_collapse_spaces(self):
        assert normalize_text("black  scholes") == "black scholes"


# ─── to_number ───────────────────────────────────────────────────────────────

class TestToNumber:
    def test_integer(self):
        assert to_number("3") == 3.0

    def test_decimal(self):
        assert to_number("0.5") == 0.5
        assert to_number(".5") == 0.5

    def test_fraction(self):
        assert to_number("1/2") == 0.5
        assert to_number("1/4") == 0.25

    def test_percentage(self):
        assert to_number("50%") == 0.5
        assert to_number("25%") == 0.25

    def test_invalid(self):
        assert to_number("delta") is None
        assert to_number("") is None
        assert to_number("N/A") is None


# ─── expand_alternatives ─────────────────────────────────────────────────────

class TestExpandAlternatives:
    def test_base_included(self):
        alts = expand_alternatives("delta")
        assert "delta" in alts

    def test_parenthesis(self):
        alts = expand_alternatives("a lot (lots)")
        assert "a lot" in alts
        assert "lots" in alts

    def test_or_separator(self):
        alts = expand_alternatives("increase or decrease")
        assert "increase" in alts
        assert "decrease" in alts

    def test_slash_with_spaces(self):
        alts = expand_alternatives("yes / no")
        assert "yes" in alts
        assert "no" in alts

    def test_fraction_not_split(self):
        # 1/2 没有空格，不应被拆开
        alts = expand_alternatives("1/2")
        assert "1/2" in alts
        # 不应出现单独的 "1" 或 "2"
        assert "1" not in alts
        assert "2" not in alts


# ─── blank_match ─────────────────────────────────────────────────────────────

class TestBlankMatch:
    def test_exact(self):
        assert blank_match("delta", "delta") is True

    def test_case_insensitive(self):
        assert blank_match("Delta", "delta") is True
        assert blank_match("DELTA", "delta") is True

    def test_trailing_punctuation(self):
        assert blank_match("delta.", "delta") is True

    def test_numbered_prefix_in_user(self):
        assert blank_match("1. delta", "delta") is True

    def test_latex_wrapper(self):
        assert blank_match("$0.5$", "0.5") is True

    def test_numeric_equivalence_fraction(self):
        assert blank_match("1/2", "0.5") is True
        assert blank_match("0.5", "1/2") is True

    def test_numeric_equivalence_pct(self):
        assert blank_match("50%", "0.5") is True
        assert blank_match("0.5", "50%") is True

    def test_numeric_equivalence_fraction_pct(self):
        assert blank_match("1/2", "50%") is True

    def test_parenthesis_alternative(self):
        assert blank_match("lots", "a lot (lots)") is True
        assert blank_match("a lot", "a lot (lots)") is True

    def test_or_alternative(self):
        assert blank_match("increase", "increase or decrease") is True
        assert blank_match("decrease", "increase or decrease") is True

    def test_no_match(self):
        assert blank_match("gamma", "delta") is False
        assert blank_match("0.3", "0.5") is False


# ─── judge_choice ─────────────────────────────────────────────────────────────

class TestJudgeChoice:
    def test_single_correct(self):
        assert judge_choice("A", {"A"}) is True
        assert judge_choice("B", {"A"}) is False

    def test_with_spaces(self):
        assert judge_choice("A, B", {"A", "B"}) is True
        assert judge_choice(" A ", {"A"}) is True

    def test_chinese_comma(self):
        assert judge_choice("A，B", {"A", "B"}) is True

    def test_multi_correct(self):
        assert judge_choice("A,C", {"A", "C"}) is True
        assert judge_choice("A,B", {"A", "C"}) is False

    def test_extra_option(self):
        assert judge_choice("A,B", {"A"}) is False

    def test_lowercase_input(self):
        assert judge_choice("a", {"A"}) is True


# ─── judge_fill ───────────────────────────────────────────────────────────────

class TestJudgeFill:
    def test_single_blank_correct(self):
        ok, per = judge_fill("delta", "delta")
        assert ok is True
        assert per == [True]

    def test_single_blank_wrong(self):
        ok, per = judge_fill("gamma", "delta")
        assert ok is False
        assert per == [False]

    def test_multi_blank_all_correct(self):
        ok, per = judge_fill("delta | 0.5", "$\\delta$ | 1/2")
        assert ok is True
        assert per == [True, True]

    def test_multi_blank_partial(self):
        ok, per = judge_fill("delta | 0.3", "$\\delta$ | 1/2")
        assert ok is False
        assert per == [True, False]

    def test_missing_blanks_padded(self):
        # 用户只填了第一空，第二空算错但不 crash
        ok, per = judge_fill("delta", "$\\delta$ | 1/2")
        assert ok is False
        assert len(per) == 2
        assert per[0] is True
        assert per[1] is False

    def test_no_solution(self):
        ok, per = judge_fill("anything", "")
        assert ok is False

    def test_numeric_fill(self):
        ok, _ = judge_fill("50%", "0.5")
        assert ok is True


# ─── format_fill_answer ───────────────────────────────────────────────────────

class TestFormatFillAnswer:
    def test_single(self):
        assert format_fill_answer("delta") == "delta"

    def test_removes_prefix(self):
        assert format_fill_answer("1. delta") == "delta"
        assert format_fill_answer("① sigma") == "sigma"

    def test_multi(self):
        result = format_fill_answer("delta | 0.5")
        assert result == "delta | 0.5"

    def test_multi_with_prefix(self):
        result = format_fill_answer("1. delta | 2. sigma")
        assert result == "delta | sigma"
