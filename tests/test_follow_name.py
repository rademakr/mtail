#!/usr/bin/env python3
"""
Regression tests for `-F`/`--follow-name` (rename-based log rotation
support added alongside plain `-f`).

Covers the livelock found during development: the first implementation
only checked for a rotated file when `more_to_read()` observed 0 new
bytes, but right after a rotation `more_to_read()` could compute a
spurious positive byte count by comparing the *new* file's size at the
path against `tell()` on the *old*, already-exhausted file descriptor.
That meant the rotation check never ran, and `readline()` looped
forever re-reading 0 bytes from the stale descriptor. `test_no_livelock_*`
below would hang (and eventually be killed by the join timeout) if that
regresses.

`mtail` has no .py extension, so it's loaded here via importlib by path,
same as tests/test_ansi_escapes.py.
"""
import importlib.machinery
import importlib.util
import os
import tempfile
import threading
import unittest

MTAIL_PATH = os.path.join(os.path.dirname(__file__), '..', 'mtail')

loader = importlib.machinery.SourceFileLoader('mtail_under_test_follow', MTAIL_PATH)
spec = importlib.util.spec_from_loader('mtail_under_test_follow', loader)
mtail = importlib.util.module_from_spec(spec)
loader.exec_module(mtail)


def _readline_with_timeout(tailer, timeout=5):
    """Runs tailer.readline() in a thread so a livelock fails the test
    instead of hanging the whole suite forever."""
    result = {}

    def target():
        result['line'] = tailer.readline()

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise AssertionError(
            "readline() did not return within %ss -- livelock?" % timeout)
    return result['line']


class FollowNameRotationTest(unittest.TestCase):

    def test_reopens_on_rename_rotation(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'app.log')
            with open(path, 'w') as f:
                f.write('line1\n')

            tailer = mtail.TailFile(path, follow=True, follow_name=True)
            self.assertEqual(_readline_with_timeout(tailer), 'line1\n')

            # rename-based rotation: old inode moves aside, a brand new
            # file is created at the same path.
            os.rename(path, path + '.1')
            with open(path, 'w') as f:
                f.write('line2\n')

            line = _readline_with_timeout(tailer)
            self.assertEqual(line, 'line2\n',
                              "expected the reopened file's content, not "
                              "a hang/livelock on the stale descriptor")

    def test_retries_while_path_missing_then_recreated(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'app.log')
            with open(path, 'w') as f:
                f.write('line1\n')

            tailer = mtail.TailFile(path, follow=True, follow_name=True)
            self.assertEqual(_readline_with_timeout(tailer), 'line1\n')

            os.remove(path)
            # while missing, more_to_read() must report "nothing yet"
            # rather than raising and ending the tail.
            self.assertEqual(tailer.more_to_read(), 0)
            self.assertEqual(tailer.more_to_read(), 0)

            with open(path, 'w') as f:
                f.write('line2\n')

            self.assertGreater(tailer.more_to_read(), 0)

    def test_plain_follow_does_not_reopen_by_name(self):
        """-f (no -F) must keep following the open descriptor only, so
        it still sees copytruncate-style rotation but not a renamed-away
        file being replaced -- this is a deliberate difference from -F,
        not a bug."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'app.log')
            with open(path, 'w') as f:
                f.write('line1\n')

            tailer = mtail.TailFile(path, follow=True, follow_name=False)
            self.assertEqual(_readline_with_timeout(tailer), 'line1\n')

            os.rename(path, path + '.1')
            with open(path, 'w') as f:
                f.write('line2\n')

            # more_to_read() must not raise even though the path it
            # opened from is gone (the fd itself is still perfectly
            # valid on POSIX), and must not pick up the new file's
            # content since follow_name is off.
            self.assertEqual(tailer.more_to_read(), 0)


if __name__ == '__main__':
    unittest.main()
