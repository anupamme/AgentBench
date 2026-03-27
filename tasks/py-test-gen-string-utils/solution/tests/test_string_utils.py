import pytest
from string_utils import slugify, truncate, camel_to_snake, pad_left, remove_vowels


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert slugify("Hello, World!") == "hello-world"

    def test_multiple_spaces(self):
        assert slugify("a  b") == "a-b"

    def test_already_slug(self):
        assert slugify("hello-world") == "hello-world"


class TestTruncate:
    def test_short_text(self):
        assert truncate("hi", 10) == "hi"

    def test_exact_length(self):
        assert truncate("hello", 5) == "hello"

    def test_long_text(self):
        result = truncate("hello world", 8)
        assert result == "hello..."
        assert len(result) == 8

    def test_custom_suffix(self):
        result = truncate("hello world", 7, suffix="--")
        assert result.endswith("--")


class TestCamelToSnake:
    def test_simple(self):
        assert camel_to_snake("camelCase") == "camel_case"

    def test_multiple_words(self):
        assert camel_to_snake("myVariableName") == "my_variable_name"

    def test_already_snake(self):
        assert camel_to_snake("snake_case") == "snake_case"

    def test_acronym(self):
        assert camel_to_snake("getHTTPResponse") == "get_http_response"


class TestPadLeft:
    def test_pads(self):
        assert pad_left("5", 3) == "  5"

    def test_no_pad_needed(self):
        assert pad_left("hello", 3) == "hello"

    def test_custom_char(self):
        assert pad_left("7", 3, "0") == "007"


class TestRemoveVowels:
    def test_basic(self):
        assert remove_vowels("hello") == "hll"

    def test_uppercase(self):
        assert remove_vowels("HELLO") == "HLL"

    def test_no_vowels(self):
        assert remove_vowels("rhythm") == "rhythm"

    def test_empty(self):
        assert remove_vowels("") == ""
