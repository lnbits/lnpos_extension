from typing import Optional

from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash

from .models import CreateLnpos, Lnpos, LnposPayment

db = Database("ext_lnpos")


async def create_lnpos(data: CreateLnpos) -> Lnpos:

    lnpos_id = urlsafe_short_hash()[:5]
    lnpos_key = urlsafe_short_hash()[:16]
    device = Lnpos(
        id=lnpos_id,
        key=lnpos_key,
        title=data.title,
        wallet=data.wallet,
        profit=data.profit or 0.0,
        currency=data.currency or "sat",
    )

    await db.insert("lnpos.lnpos", device)

    return device


async def update_lnpos(device: Lnpos) -> Lnpos:
    await db.update("lnpos.lnpos", device)
    return device


async def get_lnpos(lnpos_id: str) -> Optional[Lnpos]:
    return await db.fetchone(
        "SELECT * FROM lnpos.lnpos WHERE id = :id",
        {"id": lnpos_id},
        Lnpos,
    )


async def get_lnposs(wallet_ids: list[str]) -> list[Lnpos]:

    q = ",".join([f"'{w}'" for w in wallet_ids])
    return await db.fetchall(
        f"""
        SELECT * FROM lnpos.lnpos WHERE wallet IN ({q})
        ORDER BY id
        """,
        model=Lnpos,
    )


async def delete_lnpos(lnpos_id: str) -> None:
    await db.execute("DELETE FROM lnpos.lnpos WHERE id = :id", {"id": lnpos_id})


async def create_lnpos_payment(payment: LnposPayment) -> LnposPayment:
    await db.insert("lnpos.lnpos_payment", payment)
    return payment


async def update_lnpos_payment(
    lnpos_payment: LnposPayment,
) -> LnposPayment:
    await db.update("lnpos.lnpos_payment", lnpos_payment)
    return lnpos_payment


async def get_lnpos_payment(
    lnpos_payment_id: str,
) -> Optional[LnposPayment]:
    return await db.fetchone(
        "SELECT * FROM lnpos.lnpos_payment WHERE id = :id",
        {"id": lnpos_payment_id},
        LnposPayment,
    )


async def get_lnpos_payments(
    lnpos_ids: list[str],
) -> list[LnposPayment]:
    if len(lnpos_ids) == 0:
        return []
    q = ",".join([f"'{w}'" for w in lnpos_ids])
    return await db.fetchall(
        f"""
        SELECT * FROM lnpos.lnpos_payment WHERE lnpos_id IN ({q})
        ORDER BY id
        """,
        model=LnposPayment,
    )
