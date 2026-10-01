"""HTML and JSON report generation for SuiteResult."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

from jinja2 import Environment, select_autoescape

if TYPE_CHECKING:
    from privacyprobe.result import SuiteResult

# Autoescaping is essential: prompts and responses are untrusted model output.
_env = Environment(autoescape=select_autoescape(default=True, default_for_string=True))

BASE_CSS = """  :root { --bg:#fff; --fg:#1d1d1f; --muted:#6e6e73; --line:#e5e5ea; --pass:#1a7f37; --fail:#cf222e; --code:#f6f8fa; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#0d1117; --fg:#e6edf3; --muted:#8d96a0; --line:#30363d; --pass:#3fb950; --fail:#f85149; --code:#161b22; }
  }
  body { font: 14px/1.5 -apple-system, system-ui, sans-serif; margin: 0; padding: 24px 16px; background: var(--bg); color: var(--fg); }
  main { max-width: 1100px; margin: 0 auto; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  .meta { color: var(--muted); margin-bottom: 20px; }
  .stats { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 24px; }
  .stat { border: 1px solid var(--line); border-radius: 8px; padding: 10px 16px; min-width: 110px; }
  .stat b { display: block; font-size: 22px; }
  .pass { color: var(--pass); } .fail { color: var(--fail); }
  table { width: 100%; border-collapse: collapse; table-layout: fixed; }
  th, td { text-align: left; vertical-align: top; padding: 8px; border-bottom: 1px solid var(--line); overflow-wrap: anywhere; }
  th { color: var(--muted); font-weight: 600; }
  pre { margin: 0; white-space: pre-wrap; font-size: 12px; background: var(--code); padding: 6px; border-radius: 4px; max-height: 160px; overflow: auto; }
  .wrap { overflow-x: auto; }
"""

HTML_TEMPLATE = _env.from_string("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>privacyprobe report</title>
<style>
{{ css|safe }}</style>
</head>
<body>
<main>
  <h1>privacyprobe report</h1>
  <div class="meta">Generated {{ generated }} &middot; privacyprobe {{ version }}</div>
  <div class="stats">
    <div class="stat"><b>{{ r.total }}</b>total</div>
    <div class="stat pass"><b>{{ r.passed }}</b>passed</div>
    <div class="stat fail"><b>{{ r.failed }}</b>failed</div>
    <div class="stat"><b>{{ "%.0f"|format(r.pass_rate * 100) }}%</b>pass rate</div>
  </div>
  <div class="wrap">
  <table>
    <colgroup><col style="width:13%"><col style="width:8%"><col style="width:7%"><col style="width:24%"><col style="width:24%"><col style="width:24%"></colgroup>
    <thead><tr><th>Check</th><th>Status</th><th>Score</th><th>Details</th><th>Prompt</th><th>Response</th></tr></thead>
    <tbody>
    {% for t in r.results %}
      <tr>
        <td>{{ t.check_name }}</td>
        <td class="{{ 'pass' if t.passed else 'fail' }}">{{ 'PASS' if t.passed else 'FAIL' }}</td>
        <td>{{ "%.2f"|format(t.score) }}</td>
        <td>{{ t.details }}</td>
        <td><pre>{{ t.prompt }}</pre></td>
        <td><pre>{{ t.response }}</pre></td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  </div>
</main>
</body>
</html>
""")


def _version() -> str:
    from privacyprobe import __version__

    return __version__


def render_html(result: SuiteResult) -> str:
    return HTML_TEMPLATE.render(
        css=BASE_CSS,
        r=result,
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        version=_version(),
    )


def render_json(result: SuiteResult) -> str:
    data = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "privacyprobe_version": _version(),
        **result.to_dict(),
    }
    return json.dumps(data, indent=2, default=str)


def write_output(text: str, output: Union[str, Path]) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def generate_report(
    result: SuiteResult,
    format: str = "html",
    output: Optional[Union[str, Path]] = None,
    redact: bool = False,
) -> Path:
    """Write ``result`` as an HTML or JSON report and return the output path.

    With ``redact=True`` personal data is replaced by labels (``[EMAIL]``) in
    prompts, responses, details and metadata, so the report itself is safe to share.
    """
    renderers = {"html": render_html, "json": render_json}
    fmt = format.lower()
    if fmt not in renderers:
        raise ValueError(f"Unsupported report format {format!r}; use 'html' or 'json'")
    if redact:
        from privacyprobe.redact import redact_suite_result

        result = redact_suite_result(result)
    return write_output(renderers[fmt](result), output or f"report.{fmt}")
