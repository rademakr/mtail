# mtail

A file tailer/colorer. Python 3 port of the original `mtail` by
[Matt Hellige](mailto:matt@immute.net), which was itself derived in
part from colortail-0.3.0 by Joakim Andersson.

Not to be confused with:
- [multitail](https://github.com/folkertvanheusden/multitail) — a
  much bigger ncurses split-window multi-pane log viewer.
- [Google's `mtail`](https://github.com/google/mtail) — a log-parsing
  metrics exporter for Prometheus/StatsD.

This one just tails one or more files (or stdin), colorizing each
line based on regexes defined in `~/.mtailrc`, with per-filename
config selection so different logs get different color schemes
automatically.

## Install

```
cp mtail ~/bin/mtail   # or /usr/local/bin, wherever you like
chmod +x ~/bin/mtail
cp .mtailrc.sample ~/.mtailrc
```

Requires Python 3, no third-party dependencies.

## Usage

```
mtail [option]... [<filename>]...

  -?, -h, --help             print usage info and exit
      -f, --follow           output appended data as the file grows
      -n, --lines=N          output the last N lines, instead of the last 10
      -v, --verbose          always output headers giving file names
      -q, --quiet, --silent  never output headers giving file names
      --config=FILE          use config file FILE instead of ~/.mtailrc
      --remove-blanks        do not display blank lines
  -u, --unit=UNIT            tail this systemd unit's journal (repeatable)
  -j, --journal              tail the whole journal (journalctl, no -u filter)
      --journal-arg=ARG      pass ARG through to journalctl (repeatable)
```

With more than one filename/unit/journal source, mtail precedes each
chunk of output with a `==> source <==` header, same as GNU `tail`. If
no filenames, units, or `-j` are given, standard input is read.

Each source is tailed in its own thread, so e.g.
`mtail -f a.log -u nginx -j` follows a file, one systemd unit, and the
whole journal all at once, interleaving their output as lines arrive.

### journalctl support

```
mtail -u sshd -f                       # follow one unit
mtail -u sshd -u nginx -f              # follow several units, each own banner
mtail -j -f                            # follow the whole journal
mtail -u myapp -f --journal-arg=-p --journal-arg=err   # errors only
mtail -u myapp -f --journal-arg=--since=today
```

Journal sources are colored using the exact same `.mtailrc` rules as
files:

- A `files:` block's filename regex is matched against the **unit
  name** you passed to `-u` (so `files: /sshd/` colors both an
  `sshd.log` file and a `-u sshd` journal identically — no config
  changes needed to reuse existing rules).
- A `files: journal` block (mirrors the existing `files: stdin`) sets
  the fallback color scheme for any unit that doesn't match a more
  specific block, and for `-j`.
- `files: default` remains the final fallback, same as always.
- `-f`/`--follow` and `-n`/`--lines` are passed straight through to
  `journalctl -f` / `journalctl -n`.
- For anything journalctl supports that mtail doesn't have a
  dedicated flag for (`--since`, `-p`/`--priority`, `-k`, `-o`, ...),
  use `--journal-arg=...`, one flag+value per `=` (e.g.
  `--journal-arg=--since=1 hour ago`, not two separate args) so
  nothing needs shell-quoting gymnastics.
- Missing `journalctl` (non-systemd systems), permission errors, and
  bad unit names surface journalctl's own stderr output directly;
  that one source's thread ends quietly while any other sources you
  gave keep running.

## The `.mtailrc` format

The config file consists of `files:` blocks (one per group of files
that should share a color scheme), each optionally followed by
`filters:` and/or `colors:` sub-blocks, plus any number of `ansi:`
blocks for defining custom color names. Comments are full lines
starting with `#`.

```
files: /mail\.log/
    colors:
        /stat=Sent/    brightgreen

files: /ldap\.log/
    colors:
        /err=49/       brightgreen
        /undefined/    brightred

files: default
    colors:
        /FAILED/       brightred
```

- `files:` takes one or more filename regexes (matched against the
  file's basename, not the full path), OR the special tokens `stdin`
  (use this block when reading standard input) and `default` (use
  this block when nothing else matches). A block can combine several
  tokens, e.g. `files: stdin /stdout\.log/` uses the same colors both
  for stdin and for any file named `stdout.log`.
- The **first** `files:` block whose regex matches wins — order
  matters, top to bottom.
- `filters:` is an optional list of `/pattern/replacement/`
  substitutions applied to each line, in order, *before* coloring.
  Standard regex substitution syntax (`\1`, `\2`, ... for capture
  groups) is supported.
- `colors:` is a list of `/pattern/colorname` rules. All rules in a
  block are checked against every line; later rules paint over
  earlier ones where their matches overlap. If the pattern has one
  capture group, only that group is colored; with no group, the whole
  match is colored.
- `ansi:` blocks define custom color names as raw ANSI escapes:
  `/mycolor/\033[1;35m/`. Backslash escapes in the sequence
  (`\033`, `\x1b`, `\n`, `\t`, `\\`) are decoded, so `\033[1;35m`
  becomes a real ESC byte rather than being printed as literal text.
  These merge into (and can override) the built-in palette: `black red
  green yellow blue magenta cyan white` and their `bright*` variants,
  plus `reset`.
- The regex delimiter can be any character that isn't a letter or
  digit (`/`, `|`, `,`, ...) — pick one that isn't itself in your
  pattern, since (as in the original) the delimiter search doesn't
  respect backslash-escaping when looking for the *closing* mark, only
  when producing the final regex text.
- An unrecognized color name silently drops that one `colors:` rule
  rather than failing the whole config.

See `.mtailrc.sample` for a fuller worked example.

## What changed from the original

This is a behavioral port, not a rewrite — same DSL, same CLI, same
coloring algorithm. Ported to Python 3 (no more `getopt`/`string`
module gymnastics, `has_key`, or Python 2 `print` statements), plus a
few latent bugs fixed along the way:

- **Startup race fixed**: with multiple files, a fast-finishing file
  could previously trip the "all done" signal before a slower file's
  tailer thread had even started, silently dropping that file's
  output entirely. Now all threads are counted before any of them
  start.
- `checkconfigs()` no longer mutates a list while iterating over it
  (this used to skip checking every other unrecognized-color rule).
- The ANSI color-name table is no longer a mutable class attribute
  shared across `ConfigFile` instances.
- `colorize()` no longer risks an infinite loop on a zero-width regex
  match.
- `ansi:` sequence values now decode backslash escapes (`\033`,
  `\x1b`, `\n`, ...); previously `\033[1;35m` was stored and printed
  as literal text instead of a real ANSI escape.

Everything else — the config DSL's quirks included — is intentionally
unchanged for drop-in compatibility with an existing `.mtailrc`.
