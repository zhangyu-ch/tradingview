#!/usr/bin/env python3
"""Verify the single tolerated upstream dependency warning on Python 3.12+."""

from __future__ import annotations

import re
import sys
import warnings
from datetime import timedelta

from flask import Flask
from flask_login import LoginManager, UserMixin, login_user

EXPECTED_MESSAGE = re.compile(
    r"^datetime\.datetime\.utcnow\(\) is deprecated and scheduled for removal "
    r"in a future version\. Use timezone-aware objects to represent datetimes "
    r"in UTC: datetime\.datetime\.now\(datetime\.UTC\)\.$"
)


class _User(UserMixin):
    id = "warning-baseline-user"


def collect_warnings() -> list[warnings.WarningMessage]:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="warning-baseline-secret",
        TESTING=True,
    )
    LoginManager(app)

    @app.get("/")
    def remember_login():
        login_user(_User(), remember=True, duration=timedelta(days=1))
        return "ok"

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        response = app.test_client().get("/")

    if response.status_code != 200:
        raise AssertionError(f"warning probe request failed: {response.status_code}")
    return [item for item in caught if issubclass(item.category, DeprecationWarning)]


def main() -> int:
    if sys.version_info < (3, 12):
        print("warning baseline probe skipped: Python < 3.12")
        return 0

    caught = collect_warnings()
    matching = [
        item
        for item in caught
        if EXPECTED_MESSAGE.fullmatch(str(item.message))
        and item.filename.replace("\\", "/").endswith(
            "/flask_login/login_manager.py"
        )
    ]
    unexpected = [item for item in caught if item not in matching]

    if len(matching) != 1 or unexpected:
        details = [
            f"{item.category.__name__}: {item.message} ({item.filename}:{item.lineno})"
            for item in caught
        ]
        raise AssertionError(
            "dependency warning baseline changed; expected exactly one Flask-Login "
            f"utcnow warning, got {len(caught)}:\n" + "\n".join(details)
        )

    item = matching[0]
    print(
        "expected upstream warning baseline: "
        f"{item.category.__name__}: {item.message}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
