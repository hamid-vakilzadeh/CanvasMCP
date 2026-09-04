"""Payload-free diagnostics for the standalone local MCP process."""

import logging
import sys


def _private_record(name, level, pathname, lineno, msg, args, exc_info,
                    func=None, sinfo=None, **kwargs):
    # Never format the original message: validation errors, URLs, exception
    # chains, and arbitrary student text cannot be reliably redacted by regex.
    component = name.split(".", 1)[0]
    if component not in {"fastmcp", "mcp", "canvasAPI", "docket", "asyncio"}:
        component = "runtime"
    if level not in {logging.DEBUG, logging.INFO, logging.WARNING,
                     logging.ERROR, logging.CRITICAL}:
        level = logging.WARNING
    return logging.LogRecord(
        component, level, "", 0, "Diagnostic details suppressed for privacy.",
        (), None,
    )


def configure_private_diagnostics() -> None:
    """Keep severity/component only; call solely in the dedicated stdio process.

    The record factory discards payloads before framework handlers see them.
    Reconfigure after imports so dependency handlers cannot write log files or
    use formats that include extra fields. MCP results on stdout are unaffected.
    """
    logging.setLogRecordFactory(_private_record)
    logging.raiseExceptions = False
    logging.captureWarnings(True)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.WARNING, handlers=[handler], force=True)
    for logger in logging.Logger.manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            for existing in logger.handlers[:]:
                logger.removeHandler(existing)
                existing.close()
            logger.propagate = True
            logger.setLevel(logging.NOTSET)
