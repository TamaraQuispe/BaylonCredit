"""Create a readable, explicitly filtered view of the actual R01-R07 board."""

import html
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

source = Path(__file__).resolve().parent.parent / 'docs/APF2_Kanban.json'
board = json.loads(source.read_text())
cards = [card for card in board['cards'] if card['id'] in {f'R{index:02}' for index in range(1, 8)}]
assert len(cards) == 7
now = datetime.now(UTC).isoformat()
output = Path(sys.argv[1])
output.parent.mkdir(parents=True, exist_ok=True)
items = ''.join(f"<article><div class='top'><b>{html.escape(card['id'])}</b><span>{html.escape(card['state'])}</span></div><h2>{html.escape(card['title'])}</h2><p>{html.escape(card['owner'])}</p><small>{html.escape(card['evidence'])}</small></article>" for card in cards)
output.write_text(f"<!doctype html><html lang='es'><meta charset='utf-8'><title>Kanban R01-R07</title><style>body{{font:16px Arial;color:#0b1c30;background:#f8f9ff;margin:28px}}h1{{color:#00236f}}main{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}article{{background:white;border:1px solid #c5c5d3;border-radius:10px;padding:18px}}.top{{display:flex;justify-content:space-between;color:#00236f}}span{{background:#dce1ff;padding:4px 10px;border-radius:12px}}h2{{font-size:19px}}p,small{{line-height:1.45;color:#444651}}</style><h1>Kanban APF2 · Vista filtrada R01-R07</h1><p>Captura UTC: {now}. Estado técnico de siete mejoras. Registro completo y movimientos en kanban.json.</p><p>WIP del tablero: En curso máximo 2; Revisión máximo 2. Esta vista no muestra las tarjetas P01-P06.</p><main>{items}</main><p>Hecho significa cierre técnico, no adopción diaria ni validación de ML. Revalidación con condiciones según ficha del 08/10/2026. Las nuevas condiciones siguen abiertas.</p></html>", encoding='utf-8')
output.with_suffix('.json').write_text(json.dumps({'captured_utc': now, 'source': 'docs/APF2_Kanban.json', 'scope': 'Vista filtrada R01-R07', 'cards': cards}, ensure_ascii=False, indent=2))
print('Vista Kanban R01-R07 generada desde el registro actual.')
