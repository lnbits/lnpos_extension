from http import HTTPStatus

from Cryptodome.Cipher import AES
from fastapi import APIRouter, HTTPException, Query, Request
from lnbits.core.services import create_invoice
from lnbits.helpers import urlsafe_short_hash
from lnbits.lnurl import LnurlErrorResponseHandler
from lnbits.utils.exchange_rates import fiat_amount_as_satoshis
from loguru import logger

from .crud import (
    create_lnpos_payment,
    get_lnpos,
    get_lnpos_payment,
    update_lnpos_payment,
)
from .models import LnposPayment

lnpos_lnurl_router = APIRouter(prefix="/api/v1/lnurl")
lnpos_lnurl_router.route_class = LnurlErrorResponseHandler


async def _validate_payload(payload: str, iv: str, lnpos_id: str, key: str) -> str:
    if len(payload) % 16 != 0:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Invalid payload length.")
    if len(iv) != 32:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Invalid IV length.")
    lnpos_payment = await get_lnpos_payment(iv)
    if lnpos_payment and lnpos_payment.lnpos_id != lnpos_id:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Not your payment.")
    if lnpos_payment and lnpos_payment.payment_hash:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Payment already claimed.")
    if lnpos_payment:
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Payment already registered.")
    try:
        _iv = bytes.fromhex(iv)
        _ct = bytes.fromhex(payload)
        cipher = AES.new(key.encode(), AES.MODE_CBC, _iv)
        pt = cipher.decrypt(_ct)
        msg = pt.split(b"\x00")[0].decode()
        return msg
    except Exception as e:
        logger.debug(f"Error decrypting payload: {e}")
        logger.debug(f"Payload: {payload}")
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Invalid payload.") from e


@lnpos_lnurl_router.get("/{lnpos_id}")
async def lnurl_params(
    request: Request,
    lnpos_id: str,
    payload: str = Query(..., alias="p"),
    iv: str = Query(...),
):
    lnpos = await get_lnpos(lnpos_id)
    if not lnpos:
        return {
            "status": "ERROR",
            "reason": f"lnpos {lnpos_id} not found on this server",
        }
    msg = await _validate_payload(payload, iv, lnpos.id, lnpos.key)
    pin, amount = msg.split(":")
    if lnpos.currency == "sat":
        price_sat = int(amount)
    else:
        price_sat = await fiat_amount_as_satoshis(float(amount) / 100, lnpos.currency)
        if price_sat is None:
            return {"status": "ERROR", "reason": "Price fetch error."}
    price_sat = int(price_sat * ((lnpos.profit / 100) + 1))
    lnpos_payment = LnposPayment(
        id=urlsafe_short_hash(),
        lnpos_id=lnpos.id,
        sats=price_sat,
        pin=int(pin),
        payload="unused",
    )
    await create_lnpos_payment(lnpos_payment)
    return {
        "tag": "payRequest",
        "callback": str(
            request.url_for("lnpos.lnurl_callback", payment_id=lnpos_payment.id)
        ),
        "minSendable": price_sat * 1000,
        "maxSendable": price_sat * 1000,
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
        raise HTTPException(HTTPStatus.NOT_FOUND, detail="lnpos_payment not found.")
    lnpos = await get_lnpos(lnpos_payment.lnpos_id)
    if not lnpos:
        raise HTTPException(HTTPStatus.NOT_FOUND, detail="lnpos not found.")

    payment = await create_invoice(
        wallet_id=lnpos.wallet,
        amount=lnpos_payment.sats,
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
            "description": "Check the attached link for the pin.",
            "url": str(request.url_for("lnpos.displaypin", payment_id=payment_id)),
        },
        "routes": [],
    }
