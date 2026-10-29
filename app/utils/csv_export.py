import csv
import io
from typing import Iterable, Sequence

from fastapi.responses import StreamingResponse

_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _safe(value):
    """Neutralise spreadsheet formula injection and render None as empty."""
    if value is None:
        return ""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def rows_to_csv_response(filename: str, rows: Iterable[dict], columns: Sequence[str] | None = None) -> StreamingResponse:
    rows = list(rows)
    columns = list(columns or (rows[0].keys() if rows else []))
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([_safe(row.get(c)) for c in columns])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
