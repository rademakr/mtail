# Changelog

## 2.3.0 — -F / --follow-name

1. Added `-F`, `--follow-name` for file sources: like `-f`, but also
   follows the file *by name*. If the file is rotated (renamed away
   and a new file created at the same path, as with typical
   `logrotate` configs that don't use `copytruncate`), mtail detects
   the inode change and reopens the new file from the start. It also
   retries while the path is temporarily missing (between the rename
   and the new file's creation) instead of ending the tail. Plain
   `-f` is unchanged: it still follows the open file descriptor only,
   so it keeps working with `copytruncate`-style rotation (same
   inode, truncated in place) but not rename-based rotation.
2. While implementing the above, found and fixed a livelock: the
   initial version only checked for rotation when `more_to_read()`
   observed 0 new bytes, but after a rotation, `more_to_read()` could
   spuriously compute a positive byte count by comparing the *new*
   file's size at the path against `tell()` on the *old*, already-
   exhausted file descriptor -- so the rotation check never ran, and
   `readline()` looped forever re-reading 0 bytes from the stale
   descriptor. Fixed by checking for rotation at the top of every
   `more_to_read()` poll, before any size/position comparison, so the
   open file descriptor can never be stale when those comparisons
   happen.

## 2.2.0 — ansi: escape decoding fix

1. Fixed `ansi:` blocks not decoding backslash escapes (`\033`,
   `\x1b`, `\n`, ...) in the sequence value. The README's own example
   (`/mycolor/\033[1;35m/`) never actually worked: `_read_delimited()`
   only unescapes the delimiter character, so the sequence was stored
   as the literal 8-character text `\033[1;35m` rather than a real ESC
   byte, and that literal text got printed instead of a color. Custom
   `ansi:` names now decode the same way `DEFAULT_ANSI`'s Python
   string literals already did. See `tests/test_ansi_escapes.py`.

## 2.1.0 — journalctl support

1. Added `-u UNIT` / `--unit=UNIT` (repeatable) to tail one or more
   systemd units' journals via `journalctl -u UNIT`, and `-j` /
   `--journal` to tail the whole journal. Both can be combined with
   each other and with plain filenames in a single invocation, each
   getting its own thread, banner, and color config, same as
   multi-file mode already worked.
2. Added `--journal-arg=ARG` (repeatable) to pass arbitrary extra
   arguments through to the underlying `journalctl` call (e.g.
   `--journal-arg=--since=today`, `--journal-arg=-p` +
   `--journal-arg=err`), so anything journalctl supports remains
   reachable without mtail having to re-implement its whole flag
   surface.
3. Journal sources are colored using the *same* `.mtailrc` rules as
   files: a `files:` block's regex is matched against the unit name
   first (so `files: /sshd/` colors both an `sshd.log` file and a
   `-u sshd` journal identically); a new `files: journal` block (same
   idea as the existing `files: stdin`) sets the fallback used for any
   unit that doesn't match a more specific block; `files: default`
   remains the final fallback. No existing `.mtailrc` needs to change.
4. `-f`/`--follow` and `-n`/`--lines` are passed straight through to
   `journalctl -f` / `journalctl -n`, so journal sources follow and
   trim the same way file sources do.
5. Spawned `journalctl` subprocesses are tracked and terminated on
   exit/Ctrl-C rather than being left running in the background.
6. Fixed a second latent hang bug (present in the original too): a
   source that fails to open (missing file, or now, a bad journalctl
   invocation) calls `sys.exit(1)` from within its thread, which
   raises `SystemExit` -- not a subclass of `Exception`. The thread's
   `except Exception: pass` didn't catch it, so the active-source
   counter never decremented for that thread, and mtail would hang
   forever waiting for it even if every other source finished
   normally. Now caught with `except BaseException`.

## 2.0.0 — Python 3 port

1. Ported the original Python 2 `mtail` (by Matt Hellige) to Python 3.
   Same `.mtailrc` DSL, same CLI flags, same coloring algorithm.
2. Fixed a startup race condition where a fast-finishing file's tailer
   thread could signal "all done" before a slower file's thread had
   even started, silently dropping that file's output on multi-file
   runs.
3. Fixed `checkconfigs()` mutating the `colors` list while iterating
   over it (was silently skipping the check on every other
   unrecognized-color rule after the first removal).
4. Fixed the ANSI color-name table being a mutable class attribute
   shared across `ConfigFile` instances.
5. Fixed a potential infinite loop in `colorize()` on a zero-width
   regex match.
6. Replaced `getopt`-based argument parsing with a hand-rolled parser
   (kept close to the original's exact flag semantics) — no
   functional CLI changes.
7. Verified against a real-world `.mtailrc` (multi-block, filters +
   colors + unrecognized color name) across single-file, multi-file,
   `-f`/follow, `--remove-blanks`, and stdin routing.
