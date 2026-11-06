# Changelog

## 0.1.0

First version.

- Record model: one record per test with id, file, status, duration.
- Parsers: pytest `-v` output, pytest `-rA` short summary, JUnit XML, TAP 13/14.
- Format auto-detection.
- `testlogs parse` and `testlogs diff` commands.
- ANSI colour and carriage-return progress lines are stripped before parsing.
- A pytest log without a final summary line is reported as incomplete.
