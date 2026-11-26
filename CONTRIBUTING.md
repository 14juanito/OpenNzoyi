# Contributing

OpenNzoyi 🐝 is an **autonomous** multi-agent security auditing tool with a
reinforcement-learning IDS-evasion engine. Contributions are welcome — but one
rule comes before everything else.

## Ethical scope (non-negotiable)

OpenNzoyi is for **authorized** penetration testing on an **isolated lab you
control**, and nothing else. Every contribution must keep it that way: no
embedded offensive payloads (tools are wrappers around standard binaries), never
weaken the guardrails (scope gate, interception gate, rate limiting, logging),
and no non-consenting real targets. See [LICENSE](LICENSE) and
[docs/SECURITY.md](docs/SECURITY.md).

## First contribution

- **Share feedback.** Check [open issues](https://github.com/14juanito/OpenNzoyi/issues)
  for the same problem or proposal and add any new details there. For a new
  idea, explain what you were trying to do and what would make it easier.
- **Report a problem.** Include a short reproduction and the relevant
  environment. For a UI issue, a sanitized screenshot and the browser version
  can help. Remove credentials, private URLs, and sensitive task data before
  posting.
- **Report a security issue.** Do not open a public issue for a vulnerability;
  follow [docs/SECURITY.md](docs/SECURITY.md) to report it privately.
- **Send a small change.** A documentation correction, a tool-parser hardening,
  or a focused UI improvement is a good place to start — look for
  [`good first issue`](https://github.com/14juanito/OpenNzoyi/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).
  Check [open pull requests](https://github.com/14juanito/OpenNzoyi/pulls) for
  overlapping work and refer to the relevant issue in your PR so readers can
  find the discussion.

## Pull requests

- **Keep a few open PRs at a time.** Review is manual, one change at a time, so
  a large batch makes the queue unmanageable and slows everyone down, including
  you. If you have more changes queued, open one issue that lists them and wait
  for the current ones to be reviewed.
- **One focused change per PR.** If a change has independent parts, split it into
  a small number of PRs and say in each description what the other parts depend
  on.
- **Describe the change.** State the problem, the behavior change and what you
  tested. A pull request with no description is a request for changes.
- **Keep the invariants green.** Every PR must satisfy:
  - the original validation suite stays green — `pytest tests/test_validation.py`
    (72 tests);
  - **no LLM in the evasion loop** — `grep -rn "llm" nzoyi-core/evasion/` returns
    nothing;
  - any LLM-assisted layer has a **deterministic fallback** when the model is
    absent or fails;
  - `bash scripts/verify.sh` passes. For UI, `npm run build` passes.
- **Provider support stays generic.** Any OpenAI- or Anthropic-compatible
  endpoint works through `NZOYI_LLM_PROVIDER` and the panel config; provider
  convenience goes in as a neutral preset (name and base URL) or a docs recipe,
  with no vendor logos, promotional codes, baked vendor endpoints, or
  vendor-specific environment variables. The RL evasion loop never takes an LLM,
  by any provider.

## Updating Docker image pins

The Dockerfiles and the services in `docker-compose.yml` use readable tags
(`postgres:16-alpine`, `python:3.13-slim`, `node:20-slim`). Review these pins
regularly for upstream security updates. When refreshing a pin, prefer a tag
followed by a digest; run `docker buildx imagetools inspect <image>:<tag>` and
use the top-level index digest. Check that the index includes `linux/amd64` and
`linux/arm64` before proposing the update. Record the old and new digests in the
PR so reviewers can verify the change.

## Issues

- One problem per issue. Include the version or commit, what you ran and what you
  expected.

## Security

- Do not open a public issue for a vulnerability in OpenNzoyi itself. Follow the
  [private reporting instructions](docs/SECURITY.md).

## Local setup

```bash
git clone https://github.com/14juanito/OpenNzoyi.git
cd OpenNzoyi
pip install -r nzoyi-core/requirements.txt -r nzoyi-api/requirements.txt
bash scripts/verify.sh            # 72 tests + LLM gate + nzoyi-api tests
cd nzoyi-web && npm install && npm run dev
```
