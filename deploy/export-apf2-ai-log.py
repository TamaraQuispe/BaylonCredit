"""Export selected academic user prompts, not credentials or the whole history."""

import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

database = Path.home() / ".local/share/opencode/opencode.db"
connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
connection.row_factory = sqlite3.Row
rows = connection.execute(
    """SELECT m.id, m.time_created, json_extract(p.data, '$.text') AS prompt
    FROM message m JOIN part p ON p.message_id=m.id
    JOIN session s ON s.id=m.session_id
    WHERE s.directory=? AND json_extract(m.data, '$.role')='user'
    AND json_extract(p.data, '$.type')='text'
    AND length(json_extract(p.data, '$.text'))<1000
    AND (json_extract(p.data, '$.text') LIKE '%ficha para llenar para rildo%'
      OR json_extract(p.data, '$.text') LIKE 'facilitador: Omara%'
      OR json_extract(p.data, '$.text') LIKE '%creditos en el NAV%'
      OR json_extract(p.data, '$.text') LIKE '%tomar nuevamente las capturas%'
      OR json_extract(p.data, '$.text') LIKE '%demostracion separada%'
      OR json_extract(p.data, '$.text') LIKE '%analices este pdf%')
    ORDER BY m.time_created""",
    (str(Path(__file__).resolve().parent.parent),),
).fetchall()
records = []
for row in rows:
    timestamp = datetime.fromtimestamp(row["time_created"] / 1000, UTC)
    models = connection.execute(
        """SELECT DISTINCT json_extract(data,'$.providerID'), json_extract(data,'$.modelID')
        FROM message WHERE json_extract(data,'$.role')='assistant'
        AND json_extract(data,'$.parentID')=?""", (row["id"],),
    ).fetchall()
    records.append({
        "message_id": row["id"],
        "date_utc": timestamp.isoformat(),
        "date_lima": timestamp.astimezone(ZoneInfo("America/Lima")).isoformat(),
        "prompt": row["prompt"],
        "tool": "OpenCode",
        "models": [{"provider": item[0], "model": item[1]} for item in models],
        "human_validation": "Completar con la revisión realmente realizada por el grupo; no confundir tests con revisión humana.",
    })
connection.close()
output = Path(sys.argv[1])
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps({"source": "Historial local OpenCode, consulta académica acotada", "records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Anexo de IA: {len(records)} prompts exactos con fechas y modelos recuperados.")
