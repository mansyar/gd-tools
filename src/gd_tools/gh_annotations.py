"""Shared GitHub Actions workflow log-command escaping helpers.

Implements the escaping rules from the official "Workflow commands
for GitHub Actions" specification so that the lint and coverage
reporters produce valid annotations:

- Message data escapes ``%`` (``%25``), CR (``%0D``), LF (``%0A``).
- Property values escape message data plus ``,` (``%2C``) and
  ``:`` (``%3A``).
"""


def escape_gh_message_data(value: str) -> str:
    """Escape GitHub Actions workflow-command message data.

    Args:
        value: Raw message data (the part after ``::``).

    Returns:
        The escaped string, safe for workflow log commands.
    """
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def escape_gh_property(value: str) -> str:
    """Escape a GitHub Actions workflow-command property value.

    Args:
        value: Raw property value (e.g. a ``file=`` or ``title=``
            attribute).

    Returns:
        The escaped string, safe for use inside the property list.
    """
    escaped = escape_gh_message_data(value)
    return escaped.replace(",", "%2C").replace(":", "%3A")
