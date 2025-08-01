from http import HTTPStatus
from math import ceil

from fastapi import APIRouter, Query, Request
from lnbits.core.services import create_invoice
from lnbits.helpers import urlsafe_short_hash
from lnbits.utils.crypto import AESCipher
from lnbits.utils.exchange_rates import fiat_amount_as_satoshis
from lnurl import (
    CallbackUrl,
    LightningInvoice,
    LnurlErrorResponse,
    LnurlPayActionResponse,
    LnurlPayResponse,
    LnurlPaySuccessActionTag,
    Max144Str,
    MilliSatoshi,
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

lnpos_lnurl_router = APIRouter(prefix="/api/v1/lnurl")


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
        logger.debug(f"Payload: {payload}")
        return LnurlErrorResponse(reason="Invalid payload.")

    pin, amount_in_cent = msg.split(":")

    price_sat = (
        await fiat_amount_as_satoshis(float(amount_in_cent) / 100, lnpos.currency)
        if lnpos.currency != "sat"
        else ceil(float(amount_in_cent))
    )
    if price_sat is None:
        return LnurlErrorResponse(reason="Price fetch error.")

    price_sat = int(price_sat * ((lnpos.profit / 100) + 1))
    price_msat = price_sat * 1000

    lnpos_payment = LnposPayment(
        id=urlsafe_short_hash(),
        lnpos_id=lnpos.id,
        sats=price_sat,
        pin=int(pin),
    )
    await create_lnpos_payment(lnpos_payment)

    url = request.url_for("lnpos.lnurl_callback", payment_id=lnpos_payment.id)
    callback_url = parse_obj_as(CallbackUrl, str(url))
    return LnurlPayResponse(
        callback=callback_url,
        minSendable=MilliSatoshi(price_msat),
        maxSendable=MilliSatoshi(price_msat),
        metadata=lnpos.lnurlpay_metadata,
        # TODO remove those when lib is updated
        commentAllowed=None,
        payerData=None,
        allowsNostr=None,
        nostrPubkey=None,
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

    payment = await create_invoice(
        wallet_id=lnpos.wallet,
        amount=lnpos_payment.sats,
        memo=lnpos.title,
        unhashed_description=lnpos.lnurlpay_metadata.encode(),
        extra={"tag": "PoS"},
    )
    lnpos_payment.payment_hash = payment.payment_hash
    lnpos_payment = await update_lnpos_payment(lnpos_payment)

    pr = parse_obj_as(LightningInvoice, payment.bolt11)
    url = str(request.url_for("lnpos.displaypin", payment_id=payment_id))
    pin_url = parse_obj_as(CallbackUrl, url)
    action = UrlAction(
        # TODO remove this when lib is updated
        tag=LnurlPaySuccessActionTag.url,
        description=Max144Str("Check the attached link for the pin."),
        url=pin_url,
    )
    return LnurlPayActionResponse(pr=pr, successAction=action)
