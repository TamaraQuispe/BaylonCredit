"""Add images to the initial product catalog.

Revision ID: 20260904_0010
Revises: 20260904_0009
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260904_0010"
down_revision: str | None = "20260904_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PRODUCT_IMAGES = {
    "P001": "https://upload.wikimedia.org/wikipedia/commons/6/60/PilsenCallao.jpg",
    "P002": "https://plazavea.vteximg.com.br/arquivos/ids/525922/73035.jpg",
    "P003": "https://plazavea.vteximg.com.br/arquivos/ids/34708796/979367.jpg",
    "P004": (
        "https://upload.wikimedia.org/wikipedia/commons/2/26/"
        "Cusque%C3%B1aDorada.jpg"
    ),
    "P005": "https://plazavea.vteximg.com.br/arquivos/ids/24844290/21130.jpg",
    "P006": "https://plazavea.vteximg.com.br/arquivos/ids/34709492/20099608.jpg",
    "P007": "https://plazavea.vteximg.com.br/arquivos/ids/34709048/160490.jpg",
    "P008": "https://plazavea.vteximg.com.br/arquivos/ids/34331967/135078.jpg",
    "P009": "https://plazavea.vteximg.com.br/arquivos/ids/29320813/20281279.jpg",
    "P010": "https://plazavea.vteximg.com.br/arquivos/ids/319114/20183300.jpg",
}


def product_table() -> sa.TableClause:
    return sa.table(
        "products",
        sa.column("sku", sa.String()),
        sa.column("image_url", sa.String()),
    )


def upgrade() -> None:
    products = product_table()
    for sku, image_url in PRODUCT_IMAGES.items():
        op.execute(
            products.update()
            .where(products.c.sku == sku)
            .where(products.c.image_url.is_(None))
            .values(image_url=image_url)
        )


def downgrade() -> None:
    products = product_table()
    for sku, image_url in PRODUCT_IMAGES.items():
        op.execute(
            products.update()
            .where(products.c.sku == sku)
            .where(products.c.image_url == image_url)
            .values(image_url=None)
        )
