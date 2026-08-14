## Behavioral change summary

<!-- One paragraph describing the user-visible change. What can someone do
after this PR that they couldn't do before, or what changes for someone
who already uses cocotb-vivado? -->

## Breaking changes

<!-- Bullet list of removed kwargs, renamed APIs, default-value changes,
etc. If none, say "None." -->

## Local test output

<!-- Paste the output of `pytest -s tests/<your_test>.py` (or the
relevant subset). The CI runs lint only — it cannot exercise Vivado, so
the reviewer relies on this paste for functional confidence. -->

```
<paste pytest -s output here>
```

## Documentation diff confirmed

- [ ] `CHANGELOG.md` entry added under the appropriate heading
- [ ] `MIGRATION.md` row added (if there's a breaking change)
- [ ] Module docstrings added or updated on any new file
- [ ] `README.md` updated (if user-facing surface changed)
- [ ] `examples/` updated (if a new capability is worth showcasing)
- [ ] `ruff check .` and `mypy src/` clean locally
