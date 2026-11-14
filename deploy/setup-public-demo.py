"""Generate private environment once for the isolated server demo."""

import os
from pathlib import Path
from secrets import token_hex, token_urlsafe

path = Path(".env.demo")
if path.exists():
    raise SystemExit(".env.demo already exists; preserving credentials")
values = {
    "JWT_SECRET_KEY": token_hex(32),
    "DEMO_DB_PASSWORD": token_hex(24),
    "DEMO_USER_PASSWORD": token_urlsafe(15),
    "DEMO_ORIGIN": "https://demo-credify.168-75-71-113.sslip.io",
    "DEMO_BIND_IP": os.environ["DEMO_BIND_IP"],
}
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as file:
    file.write("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
print("Private demo environment generated; no production secrets used.")
