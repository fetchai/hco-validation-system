"""
Structured, human-friendly logging for the HCO agent.

Goals:
- One consistent format for every important event in the system.
- Step-by-step visibility for the three flows users care about:
    1. Certificate verification     (verify)
    2. Certificate generation       (generate)
    3. OneDrive PDF upload          (onedrive)
    4. Excel sheet row append       (excel)
- No raw debug spam. Use the helpers below; everything else stays at DEBUG.

Format:
    HH:MM:SS  LEVEL  CATEGORY  message  key=value key=value ...

Example:
    16:35:21  INFO   VERIFY    start                        cert_no=HCO-001
    16:35:21  INFO   VERIFY    source=excel_graph found     cert_no=HCO-001
    16:35:21  INFO   VERIFY    result=VERIFIED              cert_no=HCO-001 company="Foo Inc" duration=0.42s
"""

from __future__ import annotations

import logging
import os
import sys
import time
from contextlib import contextmanager
from typing import Any, Iterator, Optional


_CONFIGURED = False

LEVEL_DEFAULT = "INFO"
CATEGORIES = ("APP", "VERIFY", "GENERATE", "ONEDRIVE", "EXCEL", "GRAPH", "DB", "AUTH", "JOB")


_LEVEL_LABEL = {
    "DEBUG": "DEBUG",
    "INFO": "INFO ",
    "WARNING": "WARN ",
    "ERROR": "ERROR",
    "CRITICAL": "CRIT ",
}


class _StepFormatter(logging.Formatter):
    """Format every record as: HH:MM:SS  LEVEL  CHANNEL  message"""

    def format(self, record: logging.LogRecord) -> str:
        ts = time.strftime("%H:%M:%S", time.localtime(record.created))
        level = _LEVEL_LABEL.get(record.levelname, record.levelname[:5].ljust(5))
        channel = getattr(record, "category", record.name.replace("hco.", "").upper())
        channel = channel.ljust(8)
        message = record.getMessage()
        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"
        return f"{ts}  {level}  {channel}  {message}"


def configure(level: Optional[str] = None) -> None:
    """
    Initialize logging once for the whole process.

    Idempotent: safe to call multiple times.
    Honours HCO_LOG_LEVEL env var; falls back to `level` arg or INFO.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    resolved_level = (
        os.getenv("HCO_LOG_LEVEL")
        or level
        or LEVEL_DEFAULT
    ).upper()
    numeric_level = getattr(logging, resolved_level, logging.INFO)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(numeric_level)
    handler.setFormatter(_StepFormatter())

    root = logging.getLogger()
    # Replace any pre-existing handlers (e.g. logging.basicConfig in database.py)
    # so output stays consistent.
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler)
    root.setLevel(numeric_level)

    # Quiet third-party noise unless explicitly debugging them.
    for noisy in ("urllib3", "requests", "asyncio", "uagents", "websockets", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def _logger(channel: str) -> logging.LoggerAdapter:
    """Return a LoggerAdapter that pins the channel/category onto every record."""
    base = logging.getLogger(f"hco.{channel.lower()}")
    return logging.LoggerAdapter(base, {"category": channel.upper()})


def _format_kv(kv: dict[str, Any]) -> str:
    """Render key/value pairs in a stable, scannable shape."""
    parts: list[str] = []
    for key, value in kv.items():
        if value is None or value == "":
            continue
        text = str(value)
        if any(ch in text for ch in (" ", "\t", "=", '"')):
            text = '"' + text.replace('"', '\\"') + '"'
        parts.append(f"{key}={text}")
    return " ".join(parts)


def _emit(channel: str, level: int, message: str, **kv: Any) -> None:
    if not _CONFIGURED:
        configure()
    logger = _logger(channel)
    suffix = _format_kv(kv)
    text = f"{message}  {suffix}" if suffix else message
    logger.log(level, text, extra={"category": channel.upper()})


def info(channel: str, message: str, **kv: Any) -> None:
    _emit(channel, logging.INFO, message, **kv)


def warn(channel: str, message: str, **kv: Any) -> None:
    _emit(channel, logging.WARNING, message, **kv)


def error(channel: str, message: str, **kv: Any) -> None:
    _emit(channel, logging.ERROR, message, **kv)


def debug(channel: str, message: str, **kv: Any) -> None:
    _emit(channel, logging.DEBUG, message, **kv)


# ---------------------------------------------------------------------------
# Domain-specific helpers (the four flows the user asked about)
# ---------------------------------------------------------------------------


def verify_start(certificate_no: str, *, excel_first: bool) -> None:
    info("VERIFY", "start", cert_no=certificate_no, excel_first=excel_first)


def verify_source(certificate_no: str, *, source: str, status: str) -> None:
    """status: 'found' | 'not_found' | 'skipped' | 'error'"""
    info("VERIFY", f"source={source} {status}", cert_no=certificate_no)


def verify_done(certificate_no: str, *, verified: bool, duration_s: float, **extra: Any) -> None:
    result = "VERIFIED" if verified else "NOT_FOUND"
    info("VERIFY", f"result={result}", cert_no=certificate_no, duration=f"{duration_s:.2f}s", **extra)


def generate_start(*, job_id: str, cert_no: str, category: str) -> None:
    info("GENERATE", "start", job=job_id, cert_no=cert_no, category=category)


def generate_step(*, job_id: str, step: str, **kv: Any) -> None:
    info("GENERATE", f"step={step}", job=job_id, **kv)


def generate_done(*, job_id: str, cert_no: str, duration_s: float, **kv: Any) -> None:
    info("GENERATE", "done", job=job_id, cert_no=cert_no, duration=f"{duration_s:.2f}s", **kv)


def generate_failed(*, job_id: str, reason: str, **kv: Any) -> None:
    error("GENERATE", "failed", job=job_id, reason=reason, **kv)


def onedrive_upload(*, file: str, status: str = "ok", url: Optional[str] = None, **kv: Any) -> None:
    info("ONEDRIVE", f"upload {status}", file=file, url=url, **kv)


def onedrive_skipped(reason: str) -> None:
    warn("ONEDRIVE", "skipped", reason=reason)


def excel_append(*, table: str, cert_no: str, status: str = "ok", **kv: Any) -> None:
    info("EXCEL", f"append_row {status}", table=table, cert_no=cert_no, **kv)


def excel_skipped(reason: str) -> None:
    warn("EXCEL", "skipped", reason=reason)


@contextmanager
def step(channel: str, name: str, **kv: Any) -> Iterator[None]:
    """
    Context manager that logs `name start` / `name done duration=…` /
    `name failed reason=…` around a block of work.
    """
    started = time.monotonic()
    info(channel, f"{name} start", **kv)
    try:
        yield
    except Exception as exc:
        error(channel, f"{name} failed", reason=str(exc), duration=f"{time.monotonic() - started:.2f}s", **kv)
        raise
    else:
        info(channel, f"{name} done", duration=f"{time.monotonic() - started:.2f}s", **kv)
