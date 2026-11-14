"""Maintain the actual closure board and render a shareable snapshot."""

import html
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

source = Path(__file__).resolve().parent.parent / "docs/APF2_Kanban.json"
board = json.loads(source.read_text())
if len(sys.argv) > 1 and sys.argv[1] == "assign":
    _, _, card_id, owner, evidence = sys.argv
    card = next(item for item in board["cards"] if item["id"] == card_id)
    board["events"].append({"date_utc": datetime.now(UTC).isoformat(), "card": card_id, "from": card["state"], "to": card["state"], "actor": "OpenCode", "evidence": "Asignación futura confirmada: " + owner + ". " + evidence})
    card["owner"] = owner
    source.write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n")
    print(f"Assigned future follow-up: {card_id} -> {owner}")
elif len(sys.argv) > 1 and sys.argv[1] == "move":
    _, _, card_id, state, evidence = sys.argv
    if state not in {"Por hacer", "En curso", "Revisión", "Hecho", "Bloqueado"}:
        raise SystemExit("Invalid board state")
    card = next(item for item in board["cards"] if item["id"] == card_id)
    if state in board["wip"] and sum(item["state"] == state and item["id"] != card_id for item in board["cards"]) >= board["wip"][state]:
        raise SystemExit("WIP limit exceeded")
    board["events"].append({"date_utc": datetime.now(UTC).isoformat(), "card": card_id, "from": card["state"], "to": state, "actor": "OpenCode", "evidence": evidence})
    card["state"], card["evidence"] = state, evidence
    source.write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n")
    print(f"Recorded actual movement: {card_id} -> {state}")
elif len(sys.argv) > 1 and sys.argv[1] == "render":
    output = Path(sys.argv[2])
    output.with_suffix(".json").write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n")
    columns = []
    for state in ["Por hacer", "En curso", "Revisión", "Hecho", "Bloqueado"]:
        cards = [item for item in board["cards"] if item["state"] == state]
        content = "".join(f"<article><b>{html.escape(item['id'])}: {html.escape(item['title'])}</b><p>{html.escape(item['owner'])}</p><small>{html.escape(item['evidence'])}</small></article>" for item in cards)
        columns.append(f"<section><h2>{html.escape(state)} ({len(cards)})</h2>{content}</section>")
    events = "".join(f"<li>{html.escape(item['date_utc'])} · {html.escape(item['card'])} · {html.escape(item['from'])} → {html.escape(item['to'])}: {html.escape(item['evidence'])}</li>" for item in board["events"])
    output.write_text(f"<!doctype html><html lang='es'><meta charset='utf-8'><title>Kanban APF2</title><style>body{{font:15px Arial;color:#0b1c30;background:#f8f9ff;margin:30px}}main{{display:grid;grid-template-columns:repeat(5,1fr);gap:16px}}section{{background:#e5eeff;padding:14px;border-radius:12px}}h1{{color:#00236f}}h2{{font-size:18px}}article{{background:white;padding:14px;border-radius:8px;margin:14px 0;line-height:1.5}}p,small{{color:#444651}}li{{margin:8px 0}}</style><h1>{html.escape(board['title'])}</h1><p>{html.escape(board['scope'])}</p><p>WIP: En curso máximo 2; Revisión máximo 2. Captura UTC: {datetime.now(UTC).isoformat()}</p><main>{''.join(columns)}</main><h2>Movimientos registrados en esta sesión</h2><ul>{events}</ul></html>", encoding="utf-8")
    print(f"Board snapshot: {output}")
else:
    raise SystemExit("Use move CARD STATE EVIDENCE, assign CARD OWNER EVIDENCE or render OUTPUT")
