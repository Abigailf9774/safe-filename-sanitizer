import unittest

from safe_filename_sanitizer import sanitize_filename, sanitize_path_segment


class TestSanitizeFilename(unittest.TestCase):
    def test_clean_name_passes_through(self):
        self.assertEqual(sanitize_filename("hello.txt"), "hello.txt")

    def test_replaces_windows_illegal_chars(self):
        # Each of these is illegal on Windows.
        self.assertEqual(sanitize_filename("a<b"), "a_b")
        self.assertEqual(sanitize_filename("a>b"), "a_b")
        self.assertEqual(sanitize_filename("a:b"), "a_b")
        self.assertEqual(sanitize_filename('a"b'), "a_b")
        self.assertEqual(sanitize_filename("a|b"), "a_b")
        self.assertEqual(sanitize_filename("a?b"), "a_b")
        self.assertEqual(sanitize_filename("a*b"), "a_b")

    def test_replaces_path_separators(self):
        # / and \ are treated as illegal characters, not separators.
        self.assertEqual(sanitize_filename("a/b"), "a_b")
        self.assertEqual(sanitize_filename("a\\b"), "a_b")

    def test_replaces_control_characters(self):
        # Tab, newline, NUL.
        self.assertEqual(sanitize_filename("a\tb"), "a_b")
        self.assertEqual(sanitize_filename("a\nb"), "a_b")
        self.assertEqual(sanitize_filename("a\x00b"), "a_b")

    def test_collapses_underscore_runs(self):
        # Multiple illegal chars in a row become a single underscore.
        self.assertEqual(sanitize_filename("a//b"), "a_b")
        self.assertEqual(sanitize_filename("a<>b"), "a_b")
        self.assertEqual(sanitize_filename("a??b"), "a_b")

    def test_strips_leading_and_trailing_dots(self):
        self.assertEqual(sanitize_filename(".hidden"), "hidden")
        self.assertEqual(sanitize_filename("trailing."), "trailing")
        self.assertEqual(sanitize_filename("..weird.."), "weird")

    def test_strips_leading_and_trailing_spaces(self):
        self.assertEqual(sanitize_filename("  hello  "), "hello")

    def test_empty_string_becomes_underscore(self):
        self.assertEqual(sanitize_filename(""), "_")

    def test_all_illegal_becomes_underscore(self):
        self.assertEqual(sanitize_filename("<>:""/\\|?*"), "_")

    def test_reserved_windows_names_get_underscore_suffix(self):
        self.assertEqual(sanitize_filename("CON"), "CON_")
        self.assertEqual(sanitize_filename("con"), "con_")
        self.assertEqual(sanitize_filename("PRN.txt"), "PRN_.txt")
        self.assertEqual(sanitize_filename("COM1"), "COM1_")
        self.assertEqual(sanitize_filename("lpt9.log"), "lpt9_.log")

    def test_non_reserved_names_untouched(self):
        self.assertEqual(sanitize_filename("CONCEPT"), "CONCEPT")
        self.assertEqual(sanitize_filename("console.txt"), "console.txt")

    def test_truncates_to_255_bytes(self):
        # 300 'a' characters -> 300 bytes, must be cut to 255.
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        self.assertEqual(len(result.encode("utf-8")), 255)
        self.assertTrue(result.startswith("a"))

    def test_truncates_on_character_boundary(self):
        # Use a 2-byte character so truncation can land mid-sequence.
        # 'é' is 2 bytes in UTF-8. Build a string that is 254 bytes of
        # 'a' plus one 'é' (2 bytes) = 256 bytes, so it must be cut.
        name = "a" * 254 + "é"
        result = sanitize_filename(name)
        # Must be at most 255 bytes and must be valid UTF-8 (which
        # Python strings always are, so this is a sanity check).
        self.assertLessEqual(len(result.encode("utf-8")), 255)
        # The partial 'é' should have been dropped, leaving only 'a's.
        self.assertTrue(result.endswith("a"))

    def test_type_error_on_non_string(self):
        with self.assertRaises(TypeError):
            sanitize_filename(123)

    def test_mixed_real_world_input(self):
        self.assertEqual(
            sanitize_filename("my file: name?.txt"),
            "my file_ name_.txt",
        )


class TestSanitizePathSegment(unittest.TestCase):
    def test_clean_segment_passes_through(self):
        self.assertEqual(sanitize_path_segment("folder"), "folder")

    def test_dot_becomes_underscore(self):
        # sanitize_filename strips dots, so "." becomes "" then "_".
        self.assertEqual(sanitize_path_segment("."), "_")

    def test_double_dot_becomes_underscore(self):
        # sanitize_filename strips dots, so ".." becomes "" then "_".
        self.assertEqual(sanitize_path_segment(".."), "_")

    def test_still_replaces_illegal_chars(self):
        self.assertEqual(sanitize_path_segment("a/b"), "a_b")

    def test_normal_name_with_dots_kept(self):
        # Only bare "." and ".." are rejected; "a.b" is fine.
        self.assertEqual(sanitize_path_segment("a.b"), "a.b")


if __name__ == "__main__":
    unittest.main()
