import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

from places import spelling_key  # noqa: E402


def test_doubled_letter_and_accents_share_a_spelling_key():
    # When
    keys = {spelling_key("Chessières"), spelling_key("Chesières"), spelling_key("CHESIERES")}

    # Then
    assert len(keys) == 1


def test_leading_article_and_final_s_share_a_spelling_key():
    # When
    vernands, vernand = spelling_key("Les Vernands"), spelling_key("Vernand")

    # Then
    assert vernands == vernand


def test_different_names_keep_different_spelling_keys():
    # When
    chessel, chesieres = spelling_key("Chessel"), spelling_key("Chesières")

    # Then
    assert chessel != chesieres


def test_article_is_only_dropped_as_a_separate_word():
    # When
    leysin = spelling_key("Leysin")

    # Then
    assert leysin == "leysin"
