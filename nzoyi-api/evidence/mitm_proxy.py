"""mitmproxy addon — captures HTTP(S) flows as evidence.

Run alongside the orchestrator:

    mitmdump -s evidence/mitm_proxy.py --listen-port 8788

HTTP-speaking tools are pointed at ``http://127.0.0.1:8788`` (via the tool's
proxy param / HTTP_PROXY), so every request and response they make is captured
and can be linked to the finding it proves.

``mitmproxy`` is imported lazily so this module (and the EvidenceStore it uses)
stays importable and testable on a host without mitmproxy installed.
"""

from __future__ import annotations

import os

from evidence.capture import GLOBAL_STORE, EvidenceStore

LISTEN_PORT = int(os.environ.get("NZOYI_MITM_PORT", "8788"))


class EvidenceAddon:
    """mitmproxy addon: one capture per completed response flow."""

    def __init__(self, store: EvidenceStore | None = None, task_id: str | None = None):
        self.store = store or GLOBAL_STORE
        self.task_id = task_id or os.environ.get("NZOYI_TASK_ID")

    def response(self, flow) -> None:  # noqa: ANN001 (mitmproxy HTTPFlow)
        req = flow.request
        resp = flow.response
        self.store.capture(
            task_id=self.task_id,
            request_method=req.method,
            request_url=req.pretty_url,
            request_headers=dict(req.headers),
            request_body=req.raw_content or b"",
            response_status=resp.status_code if resp else None,
            response_headers=dict(resp.headers) if resp else {},
            response_body=(resp.raw_content or b"") if resp else b"",
        )


# mitmproxy discovers addons via a module-level ``addons`` list.
addons = [EvidenceAddon()]
