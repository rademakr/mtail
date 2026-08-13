#!/usr/bin/env python3
"""
Regression test for the ansi: block not decoding backslash escapes
(e.g. \\033) into real ANSI escape bytes. `mtail` has no .py extension,
so it's loaded here via importlib by path.
"""
import importlib.machinery
import importlib.util
import os
import tempfile
import unittest

MTAIL_PATH = os.path.join(os.path.dirname(__file__), '..', 'mtail')

loader = importlib.machinery.SourceFileLoader('mtail_under_test', MTAIL_PATH)
spec = importlib.util.spec_from_loader('mtail_under_test', loader)
mtail = importlib.util.module_from_spec(spec)
loader.exec_module(mtail)


class DecodeAnsiEscapesTest(unittest.TestCase):

    def test_octal_escape(self):
        self.assertEqual(mtail._decode_ansi_escapes(r'\033[1;35m'), '\033[1;35m')

    def test_hex_escape(self):
        self.assertEqual(mtail._decode_ansi_escapes(r'\x1b[1;35m'), '\033[1;35m')

    def test_simple_escapes(self):
        self.assertEqual(mtail._decode_ansi_escapes(r'\n\t\\'), '\n\t\\')

    def test_unrecognized_escape_left_untouched(self):
        self.assertEqual(mtail._decode_ansi_escapes(r'\q'), '\\q')


class AnsiBlockParsingTest(unittest.TestCase):
    """End-to-end: an ansi: block using \\033 syntax (as documented in
    the README) must produce a real ESC byte in the resulting color
    table, matching how DEFAULT_ANSI's Python string literals work."""

    def test_custom_ansi_name_decodes_to_real_escape(self):
        with tempfile.TemporaryDirectory() as d:
            rc_path = os.path.join(d, '.mtailrc')
            with open(rc_path, 'w') as f:
                f.write(
                    'ansi:\n'
                    '    /mycolor/\\033[1;35m/\n'
                    '\n'
                    'files: default\n'
                    '    colors:\n'
                    '        /^.*$/    mycolor\n'
                )
            config = mtail.ConfigFile(rc_path)
            config.loadconfig()
            self.assertEqual(config.ansi['mycolor'], '\033[1;35m')


if __name__ == '__main__':
    unittest.main()
