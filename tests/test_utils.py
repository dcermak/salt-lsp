from salt_lsp.utils import get_last_element_of_iterator


def test_last_element_of_range():
    assert get_last_element_of_iterator(range(10)) == 9


def test_last_element_of_empty_range():
    assert get_last_element_of_iterator(range(0)) is None
