import base64
from http import HTTPStatus

from fastapi import APIRouter, Query, Request
from lnbits.core.services import create_invoice
from lnbits.helpers import urlsafe_short_hash
from lnbits.utils.exchange_rates import fiat_amount_as_satoshis

from .crud import (
    create_lnpos_payment,
    get_lnpos,
    get_lnpos_payment,
    update_lnpos_payment,
)
from .helpers import xor_decrypt
from .models import LnposPayment

lnpos_lnurl_router = APIRouter(prefix="/api/v1/lnurl")


@lnpos_lnurl_router.get(
    "/{lnpos_id}",
    status_code=HTTPStatus.OK,
    name="lnpos.lnurl_v1_params",
)
async def lnurl_v1_params(
    request: Request,
    lnpos_id: str,
    p: str = Query(None),
):
    lnpos = await get_lnpos(lnpos_id)
    if not lnpos:
        return {
            "status": "ERROR",
            "reason": f"lnpos {lnpos_id} not found on this server",
        }

    if len(p) % 4 > 0:
        p += "=" * (4 - (len(p) % 4))

    data = base64.urlsafe_b64decode(p)
    try:
        pin, amount_in_cent = xor_decrypt(lnpos.key.encode(), data)
    except Exception as exc:
        return {"status": "ERROR", "reason": str(exc)}

    price_msat = (
        await fiat_amount_as_satoshis(float(amount_in_cent) / 100, lnpos.currency)
        if lnpos.currency != "sat"
        else amount_in_cent
    )
    if price_msat is None:
        return {"status": "ERROR", "reason": "Price fetch error."}

    price_msat = int(price_msat * ((lnpos.profit / 100) + 1))

    lnpos_payment = LnposPayment(
        id=urlsafe_short_hash(),
        lnpos_id=lnpos.id,
        payload=p,
        sats=price_msat * 1000,
        pin=int(pin),
    )
    await create_lnpos_payment(lnpos_payment)
    return {
        "tag": "payRequest",
        "callback": str(
            request.url_for("lnpos.lnurl_callback", payment_id=lnpos_payment.id)
        ),
        "minSendable": price_msat * 1000,
        "maxSendable": price_msat * 1000,
        "metadata": lnpos.lnurlpay_metadata,
    }


@lnpos_lnurl_router.get(
    "/cb/{payment_id}",
    status_code=HTTPStatus.OK,
    name="lnpos.lnurl_callback",
)
async def lnurl_callback(request: Request, payment_id: str):
    lnpos_payment = await get_lnpos_payment(payment_id)
    if not lnpos_payment:
        return {"status": "ERROR", "reason": "lnpos_payment not found."}
    lnpos = await get_lnpos(lnpos_payment.lnpos_id)
    if not lnpos:
        return {"status": "ERROR", "reason": "lnpos not found."}

    payment = await create_invoice(
        wallet_id=lnpos.wallet,
        amount=int(lnpos_payment.sats / 1000),
        memo=lnpos.title,
        unhashed_description=lnpos.lnurlpay_metadata.encode(),
        extra={"tag": "PoS"},
    )
    lnpos_payment.payment_hash = payment.payment_hash
    lnpos_payment = await update_lnpos_payment(lnpos_payment)

    return {
        "pr": payment.bolt11,
        "successAction": {
            "tag": "url",
            "description": "Check the attached link",
            "url": str(request.url_for("lnpos.displaypin", payment_id=payment_id)),
        },
        "routes": [],
    }
