"""Errors shared by alert storage and its HTTP adapter without importing a DB."""


class DuplicateAlertTaskError(ValueError):
    """A task with this name already exists in the same market."""

    def __init__(self):
        super().__init__("同一市场已存在该名称的监控任务，请使用其他任务名称")
