from http import HTTPStatus
from math import ceil

from fastapi import APIRouter, Query, Request
from lnbits.core.services import create_invoice
from lnbits.utils.crypto import AESCipher
from lnbits.utils.exchange_rates import fiat_amount_as_satoshis
from lnurl import (
    CallbackUrl,
    LightningInvoice,
    LnurlErrorResponse,
    LnurlPayActionResponse,
    LnurlPayResponse,
    Max144Str,
    MilliSatoshi,
    Url,
    UrlAction,
)
from loguru import logger
from pydantic import parse_obj_as

from .crud import (
    create_lnpos_payment,
    get_lnpos,
    get_lnpos_payment,
    update_lnpos_payment,
)
from .models import LnposPayment

lnpos_lnurl_router = APIRouter(prefix="/api/v2/lnurl")


@lnpos_lnurl_router.get("/{lnpos_id}")
async def lnurl_params(
    request: Request,
    lnpos_id: str,
    payload: str = Query(..., alias="p"),
) -> LnurlPayResponse | LnurlErrorResponse:
    lnpos = await get_lnpos(lnpos_id)
    if not lnpos:
        return LnurlErrorResponse(reason="lnpos not found.")

    if len(payload) % 22 != 0:
        return LnurlErrorResponse(reason="Invalid payload length.")
    try:
        aes = AESCipher(lnpos.key)
        msg = aes.decrypt(payload, urlsafe=True)
    except Exception as e:
        logger.debug(f"Error decrypting payload: {e}")
        return LnurlErrorResponse(reason="Invalid payload.")

    pin, amount_in_cent = msg.split(":")
    amount = float(amount_in_cent) / 100

    price_sat = (
        await fiat_amount_as_satoshis(amount, lnpos.currency)
        if lnpos.currency != "sat"
        else ceil(float(amount_in_cent))
    )
    if price_sat is None:
        return LnurlErrorResponse(reason="Price fetch error.")

    price_sat = int(price_sat * ((lnpos.profit / 100) + 1))

    # Using the payload saves the db getting spammed with the same payment
    lnpos_payment = await get_lnpos_payment(payload)
    if not lnpos_payment:
        lnpos_payment = LnposPayment(
            id=payload,
            lnpos_id=lnpos.id,
            sats=price_sat,
            pin=int(pin),
            amount=amount if lnpos.currency != "sat" else None,
        )
        await create_lnpos_payment(lnpos_payment)

    url = request.url_for("lnpos.lnurl_callback", payment_id=lnpos_payment.id)
    callback_url = parse_obj_as(CallbackUrl, str(url))
    return LnurlPayResponse(
        callback=callback_url,
        minSendable=MilliSatoshi(lnpos_payment.sats * 1000),
        maxSendable=MilliSatoshi(lnpos_payment.sats * 1000),
        metadata=lnpos.lnurlpay_metadata,
    )


@lnpos_lnurl_router.get(
    "/cb/{payment_id}",
    status_code=HTTPStatus.OK,
    name="lnpos.lnurl_callback",
)
async def lnurl_callback(
    request: Request, payment_id: str
) -> LnurlPayActionResponse | LnurlErrorResponse:
    lnpos_payment = await get_lnpos_payment(payment_id)
    if not lnpos_payment:
        return LnurlErrorResponse(reason="lnpos_payment not found.")
    lnpos = await get_lnpos(lnpos_payment.lnpos_id)
    if not lnpos:
        return LnurlErrorResponse(reason="lnpos not found.")

    extra: dict[str, str | float] = {
        "tag": "PoS",
        "pos_id": lnpos_payment.lnpos_id,
        "pos_payment_id": lnpos_payment.id,
    }

    if lnpos.currency != "sat" and lnpos_payment.amount:
        extra["requested_amount"] = lnpos_payment.amount
        extra["requested_currency"] = lnpos.currency

    payment = await create_invoice(
        wallet_id=lnpos.wallet,
        amount=lnpos_payment.sats,
        memo=lnpos.title,
        unhashed_description=lnpos.lnurlpay_metadata.encode(),
        extra=extra,
    )
    lnpos_payment.payment_hash = payment.payment_hash
    lnpos_payment = await update_lnpos_payment(lnpos_payment)

    pr = parse_obj_as(LightningInvoice, payment.bolt11)
    url = str(request.url_for("lnpos.displaypin", payment_id=payment_id))
    pin_url = parse_obj_as(Url, url)
    action = UrlAction(
        description=Max144Str("Check the attached link for the pin."),
        url=pin_url,
    )
    return LnurlPayActionResponse(pr=pr, successAction=action)
