# Messaging channels

There is currently no built-in external notification channel. Monitoring continues to execute
strategies and store events in the database; users view those events in the Web alert panel.

Feishu was retired in B4 because its sender was no longer connected to monitoring, while shared
proxy utilities still eagerly imported its large SDK. The sender, settings UI, task switch,
configuration template, and SDK dependency have been removed. Historical source and restoration
instructions are in [`archive/feishu-notifications.md`](../archive/feishu-notifications.md).
Existing private configuration, historical cache rows, and secret files are not automatically
removed or read; operators may back up and clear them, and revoke unused external credentials.

The legacy DingTalk custom-robot helper was previously removed because its API path was retired,
its configuration keys were missing, and there were no active callers.

Reintroducing a channel requires a typed configuration contract, explicit enable/disable semantics,
bounded HTTP timeouts, status validation, secret redaction, and per-market routing tests. Notification
SDKs must be optional and lazily imported outside shared proxy or market-data utilities. Persisting
an alert must not depend on successful delivery; retries need an idempotent delivery ID. Restoring
old source alone is insufficient: connect the sender to the current alert execution path and add
end-to-end regression tests without overwriting newer DB migrations or security fixes.
