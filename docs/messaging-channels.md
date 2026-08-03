# Messaging channels

The built-in notification channel is Feishu. The legacy DingTalk custom-robot helper has been removed because its API path was already documented as retired, the configuration template did not define the referenced keys, the HK branch was unreachable, and the repository had no active callers.

Reintroducing a channel requires a typed configuration contract, explicit enable/disable semantics, bounded HTTP timeouts, status validation, secret redaction, and per-market routing tests. It must not be restored by copying the removed `send_dd_msg` helper.
