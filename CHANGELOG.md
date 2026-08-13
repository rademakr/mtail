# Changelog

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
