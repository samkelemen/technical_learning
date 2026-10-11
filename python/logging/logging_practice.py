"""
═══════════════════════════════════════════════════════════════════════════════
 PRACTICE ASSIGNMENT: Build a Simple Logger from Scratch (Python 3.13)
═══════════════════════════════════════════════════════════════════════════════

GOAL
    Build a tiny logging library *by hand* (not the stdlib `logging` module) and
    wire it into a very small demo program. Building it yourself teaches the
    pieces a real logger is made of: levels, records, formatting, filtering,
    and "sinks" (where output goes).

WHY FROM SCRATCH?
    The stdlib `logging` module already does all this. The point here is to
    practice modern Python, not to ship a logger. The final "Stretch" step
    shows how this maps onto the real `logging` module.

PREREQUISITES
    Python 3.13+.  Check with:   python3 --version
    No third-party packages required (standard library only).

HOW TO WORK THROUGH THIS
    1. Read a STEP, read its TODOs.
    2. Replace the `raise NotImplementedError(...)` body with your code.
    3. Run the file:        python3 simple_logger_assignment.py
       At first it stops at STEP 1 with NotImplementedError. As you implement
       each step, the self-check at the bottom gets further before failing.
    4. When everything passes you'll see "✅ ALL CHECKS PASSED".

CHECKLIST  (tick these off as you go)
    [x] STEP 1  LogLevel enum
    [ ] STEP 2  LogRecord dataclass
    [ ] STEP 3  format_record()
    [ ] STEP 4  Sink protocol + ConsoleSink + ListSink
    [ ] STEP 5  Logger class
    [ ] STEP 6  Demo program: process_orders()
    [ ] STEP 7  (bonus) copy.replace redaction
    [ ] STEP 8  (bonus) @deprecated alias, TypeIs guard, Path.full_match
    [ ] STEP 9  (stretch) ideas only — no code required

ESTIMATED TIME: 45–90 minutes. The bonus/stretch steps are optional.
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import IntEnum
from pathlib import Path
import sys
from typing import Protocol, TypeIs
from warnings import deprecated  # PEP 702, added in Python 3.13

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Define the log levels
# ─────────────────────────────────────────────────────────────────────────────
# A logger needs ordered severity levels so it can filter ("only show WARNING
# and above"). We use IntEnum so DEBUG < INFO < WARNING < ... compares naturally,
# while `.name` still gives the human-readable string ("INFO").
#
# We copy the stdlib numbering (10/20/30/40/50) so your mental model matches the
# real `logging` module.
#
# TODO 1.1: Add the five members below with these exact values:
#               DEBUG = 10, INFO = 20, WARNING = 30, ERROR = 40, CRITICAL = 50
# TODO 1.2: Delete the `pass` once you've added members.
#
# HINT: Because IntEnum members ARE ints, `LogLevel.WARNING >= LogLevel.INFO`
#       just works — that's the whole reason we picked IntEnum over StrEnum here.
#       (StrEnum is great when you want the *value* to be a string, e.g. config
#        files — but it gives you no natural ordering for filtering.)


class LogLevel(IntEnum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Define the LogRecord
# ─────────────────────────────────────────────────────────────────────────────
# Every log call produces one immutable record. We use a frozen, slotted
# dataclass:
#   - frozen=True  -> records can't be mutated after creation (safer logs).
#   - slots=True   -> smaller/faster instances; no accidental attributes.
#
# TODO 2.1: Add these fields with type annotations, IN THIS ORDER:
#               level: LogLevel
#               message: str
#               timestamp: datetime
#               logger_name: str = "root"        # default value
# TODO 2.2: Remove the `placeholder` line once your fields exist.
#
# HINT: Order matters for positional construction in the self-check.
# HINT: A frozen dataclass automatically supports `copy.replace(record, ...)`
#       in Python 3.13 — you'll use that in STEP 7.


@dataclass(frozen=True, slots=True)
class LogRecord:
    level: LogLevel
    message: str
    timestamp: datetime
    logger_name: str = "root"


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Format a record into a line of text
# ─────────────────────────────────────────────────────────────────────────────
# Turn a LogRecord into a single human-readable string, e.g.:
#
#     2025-05-28T14:03:11Z [INFO    ] orders: shipped order 42
#
# TODO 3.1: Build the timestamp string. Use ISO 8601 with seconds precision:
#               record.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
#           (We log in UTC, hence the trailing "Z".)
# TODO 3.2: Build the level tag, left-justified to width 8 so columns line up:
#               record.level.name.ljust(8)        # e.g. "INFO    "
# TODO 3.3: Return an f-string in this exact shape:
#               f"{ts} [{level_tag}] {record.logger_name}: {record.message}"
#
# HINT: f-strings support `=` for debugging (f"{x=}") — handy while testing.


def format_record(record: LogRecord) -> str:
    timestamp = record.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")  # Log in UTC
    level_tag = record.level.name.ljust(8)
    return f"{timestamp=} [{level_tag=}] {record.logger_name=}: {record.message=}"


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Sinks (where formatted lines actually go)
# ─────────────────────────────────────────────────────────────────────────────
# A "sink" is anything that can accept a line of text. We define the shape with
# a Protocol (structural typing): any object with a matching `write(line)` method
# counts as a Sink — no inheritance required.
#
# TODO 4.1: In ConsoleSink.write, print the line to stdout.
#           (Real loggers send errors to stderr; that's a stretch goal.)
# TODO 4.2: In ListSink.write, append the line to self.lines.
#           ListSink is used by the self-check to inspect output without
#           printing — it's your test double.


class Sink(Protocol):
    """Anything with a write(line) method is a valid sink."""

    def write(self, line: str) -> None: ...


class ConsoleSink:
    """Writes log lines to standard output."""

    def write(self, line: str) -> None:
        sys.stderr.write(line)


@dataclass
class ListSink:
    """Collects log lines in memory (used for testing)."""

    lines: list[str] = field(default_factory=list)

    def write(self, line: str) -> None:
        self.lines.append(line)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — The Logger
# ─────────────────────────────────────────────────────────────────────────────
# The Logger ties everything together:
#   - it has a name and a minimum level (the filter),
#   - it owns a list of sinks,
#   - its `log()` method builds a record, drops it if below min level,
#     formats it, and fans it out to every sink.
#
# TODO 5.1 (__init__): store name, min_level, and sinks.
#           For sinks: if None was passed, default to a single ConsoleSink:
#               self.sinks: list[Sink] = sinks if sinks is not None else [ConsoleSink()]
#
# TODO 5.2 (log): the core method.
#           a) FILTER: if level < self.min_level, return immediately.
#           b) BUILD:  record = LogRecord(
#                          level=level,
#                          message=message,
#                          timestamp=datetime.now(UTC),   # 3.11+ UTC alias
#                          logger_name=self.name,
#                      )
#           c) FORMAT: line = format_record(record)
#           d) DISPATCH: for sink in self.sinks: sink.write(line)
#
# TODO 5.3 (convenience methods): implement debug/info/warning/error/critical
#           so each just calls self.log(<that level>, message).
#           e.g.  def info(self, message: str) -> None:
#                     self.log(LogLevel.INFO, message)
#
# HINT: You can write the five convenience methods by hand (clearest), or get
#       fancy later. Clear beats clever for a first pass.


class Logger:
    def __init__(
        self,
        name: str,
        min_level: LogLevel = LogLevel.INFO,
        sinks: list[Sink] | None = None,
    ) -> None:
        raise NotImplementedError("STEP 5.1: implement Logger.__init__()")

    def log(self, level: LogLevel, message: str) -> None:
        raise NotImplementedError("STEP 5.2: implement Logger.log()")

    # TODO 5.3: implement the five convenience methods below.
    def debug(self, message: str) -> None:
        raise NotImplementedError("STEP 5.3: implement debug()")

    def info(self, message: str) -> None:
        raise NotImplementedError("STEP 5.3: implement info()")

    def warning(self, message: str) -> None:
        raise NotImplementedError("STEP 5.3: implement warning()")

    def error(self, message: str) -> None:
        raise NotImplementedError("STEP 5.3: implement error()")

    def critical(self, message: str) -> None:
        raise NotImplementedError("STEP 5.3: implement critical()")

    # ── STEP 8 lives inside the class — see that section below ──


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — A very simple program that uses your logger
# ─────────────────────────────────────────────────────────────────────────────
# Pretend we process a batch of "orders". Each order is a (id, amount) tuple.
# Rules:
#   - amount <= 0      -> log an ERROR, skip the order
#   - amount > 1000    -> log a WARNING ("large order"), then process it
#   - otherwise        -> log INFO ("processed order N")
#   - at the end       -> log INFO with the count of successfully processed orders
#
# TODO 6.1: Implement the loop using a match statement on the amount.
#           Skeleton:
#               processed = 0
#               for order_id, amount in orders:
#                   match amount:
#                       case n if n <= 0:
#                           logger.error(f"order {order_id}: bad amount {amount}")
#                       case n if n > 1000:
#                           logger.warning(f"order {order_id}: large amount {amount}")
#                           processed += 1
#                       case _:
#                           logger.info(f"order {order_id}: processed")
#                           processed += 1
#               logger.info(f"done: {processed}/{len(orders)} orders processed")
#               return processed
#
# TODO 6.2: Return the number of successfully processed orders.


def process_orders(orders: list[tuple[int, float]], logger: Logger) -> int:
    raise NotImplementedError("STEP 6: implement process_orders()")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 (BONUS) — Redacting a record with copy.replace()  [Python 3.13]
# ─────────────────────────────────────────────────────────────────────────────
# Because LogRecord is a frozen dataclass, Python 3.13's copy.replace() can make
# a modified COPY without mutating the original. Useful for scrubbing secrets.
#
# TODO 7.1: Return a NEW record whose `message` is "[REDACTED]" but every other
#           field is unchanged:
#               return copy.replace(record, message="[REDACTED]")
#
# HINT: copy.replace(obj, **changes) works on any object implementing
#       __replace__ — dataclasses get it for free in 3.13.


def redact(record: LogRecord) -> LogRecord:
    raise NotImplementedError("STEP 7: implement redact() using copy.replace()")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 (BONUS) — @deprecated, TypeIs, and Path.full_match  [Python 3.13]
# ─────────────────────────────────────────────────────────────────────────────
#
# 8a) DEPRECATION (PEP 702): add a `warn()` method to Logger that forwards to
#     `warning()` but is marked deprecated. Type checkers and `python -W error`
#     will flag any caller. Add THIS method inside the Logger class above:
#
#         @deprecated("Logger.warn() is deprecated; use Logger.warning() instead")
#         def warn(self, message: str) -> None:
#             self.warning(message)
#
#     (Yes — go back up to STEP 5's class and paste it in. Then it's covered by
#      the self-check.)
#
# 8b) TYPE NARROWING (PEP 742, TypeIs): implement is_log_level() so a type
#     checker narrows `object` to `LogLevel` in the True branch.
#       TODO 8.1:  return isinstance(value, LogLevel)
#
# 8c) PATH MATCHING: Path.full_match() does glob matching on the WHOLE path
#     (new in 3.13; unlike .match() which only matches from the right).
#       TODO 8.2: return [p for p in paths if p.full_match(pattern)]


def is_log_level(value: object) -> TypeIs[LogLevel]:
    raise NotImplementedError("STEP 8b: implement is_log_level()")


def select_log_files(paths: list[Path], pattern: str = "logs/*.log") -> list[Path]:
    raise NotImplementedError("STEP 8c: implement select_log_files() with full_match()")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 9 (STRETCH — ideas only, no required code)
# ─────────────────────────────────────────────────────────────────────────────
#   • FileSink: write lines to a file with pathlib, e.g.
#         self.path.open("a", encoding="utf-8").write(line + "\n")
#   • Route ERROR/CRITICAL to sys.stderr, lower levels to sys.stdout.
#   • JSON formatter: format_record_json() -> json.dumps({...}) for log shippers.
#   • A context manager that times a block and logs the duration:
#         with logger.timed("import"): do_work()
#   • Swap to the real thing: `import logging; logging.basicConfig(level=...)`
#     and notice how your level/record/formatter/handler map onto
#     logging.{Level, LogRecord, Formatter, Handler}.
#   • Thread-safety: on a free-threaded (no-GIL) 3.13 build, sinks sharing a
#     file would need a lock. Where would you add one?
# ─────────────────────────────────────────────────────────────────────────────


# ═════════════════════════════════════════════════════════════════════════════
#  SELF-CHECK HARNESS  (you don't need to edit below this line)
#  Run the file; it verifies each step and tells you what's still missing.
# ═════════════════════════════════════════════════════════════════════════════
def _self_check() -> None:
    # STEP 1
    assert (
        LogLevel.DEBUG
        < LogLevel.INFO
        < LogLevel.WARNING
        < LogLevel.ERROR
        < LogLevel.CRITICAL
    ), "STEP 1: levels are not correctly ordered"
    assert int(LogLevel.WARNING) == 30, "STEP 1: WARNING should equal 30"
    assert LogLevel.INFO.name == "INFO", "STEP 1: .name should be 'INFO'"
    print("✓ STEP 1  LogLevel")

    # STEP 2
    rec = LogRecord(
        level=LogLevel.INFO,
        message="hello",
        timestamp=datetime(2025, 5, 28, 14, 3, 11, tzinfo=UTC),
    )
    assert rec.logger_name == "root", "STEP 2: logger_name default should be 'root'"
    try:
        rec.message = "x"  # type: ignore[misc]
        raise AssertionError("STEP 2: record should be frozen (immutable)")
    except (AttributeError, TypeError):
        pass
    print("✓ STEP 2  LogRecord")

    # STEP 3
    line = format_record(rec)
    assert "2025-05-28T14:03:11Z" in line, "STEP 3: timestamp format is wrong"
    assert "[INFO" in line and "root: hello" in line, "STEP 3: line layout is wrong"
    print("✓ STEP 3  format_record")

    # STEP 4 + STEP 5
    sink = ListSink()
    log = Logger("orders", min_level=LogLevel.INFO, sinks=[sink])
    log.debug("should be filtered out")  # below min_level -> dropped
    log.info("kept")
    assert (
        len(sink.lines) == 1
    ), "STEP 5: level filtering not working (debug leaked through)"
    assert (
        "orders: kept" in sink.lines[0]
    ), "STEP 4/5: dispatch or name handling is wrong"
    print("✓ STEP 4  Sinks")
    print("✓ STEP 5  Logger")

    # STEP 6
    sink2 = ListSink()
    log2 = Logger("orders", min_level=LogLevel.DEBUG, sinks=[sink2])
    count = process_orders([(1, 50.0), (2, -5.0), (3, 5000.0)], log2)
    assert count == 2, f"STEP 6: expected 2 processed, got {count}"
    joined = "\n".join(sink2.lines)
    assert (
        "ERROR" in joined and "WARNING" in joined
    ), "STEP 6: missing error/warning logs"
    print("✓ STEP 6  process_orders")

    # ── Bonus steps: only checked if you implemented them ──
    bonus_done = []

    try:
        red = redact(rec)
        assert red.message == "[REDACTED]" and red.level == rec.level
        assert rec.message == "hello", "redact must NOT mutate the original"
        bonus_done.append("STEP 7  copy.replace")
    except NotImplementedError:
        pass

    try:
        assert is_log_level(LogLevel.INFO) is True
        assert is_log_level("INFO") is False
        bonus_done.append("STEP 8b TypeIs guard")
    except NotImplementedError:
        pass

    try:
        files = [Path("logs/app.log"), Path("logs/sub/app.log"), Path("notes.txt")]
        kept = select_log_files(files)
        assert kept == [Path("logs/app.log")], f"full_match returned {kept}"
        bonus_done.append("STEP 8c Path.full_match")
    except NotImplementedError:
        pass

    if hasattr(Logger, "warn"):
        bonus_done.append("STEP 8a @deprecated warn()")

    for b in bonus_done:
        print(f"✓ {b}  (bonus)")

    print(
        "\n✅ ALL CHECKS PASSED"
        + (" (including bonuses!)" if len(bonus_done) >= 4 else "")
    )


if __name__ == "__main__":
    print("Running self-check...\n")
    _self_check()
