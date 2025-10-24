import base64
import hmac
from http import HTTPStatus
from io import BytesIO

from embit import compact
from fastapi import APIRouter, HTTPException, Query, Request
from lnbits.core.services import create_invoice
from lnbits.helpers import urlsafe_short_hash
from lnbits.utils.exchange_rates import fiat_amount_as_satoshis

from .crud import (
    create_lnpos_payment,
    get_lnpos,
    get_lnpos_payment,
    update_lnpos_payment,
)
from .models import LnposPayment

lnpos_lnurl_legacy_router = APIRouter(prefix="/api/v1/lnurl", deprecated=True)


def xor_decrypt(key, blob):
    s = BytesIO(blob)
    variant = s.read(1)[0]
    if variant != 1:
        raise RuntimeError("Not implemented")
    # reading nonce
    nonce_len = s.read(1)[0]
    nonce = s.read(nonce_len)
    if len(nonce) != nonce_len:
        raise RuntimeError("Missing nonce bytes")
    if nonce_len < 8:
        raise RuntimeError("Nonce is too short")

    # reading payload
    payload_len = s.read(1)[0]
    payload = s.read(payload_len)
    if len(payload) > 32:
        raise RuntimeError("Payload is too long for this encryption method")
    if len(payload) != payload_len:
        raise RuntimeError("Missing payload bytes")
    hmacval = s.read()
    expected = hmac.new(
        key, b"Data:" + blob[: -len(hmacval)], digestmod="sha256"
    ).digest()
    if len(hmacval) < 8:
        raise RuntimeError("HMAC is too short")
    if hmacval != expected[: len(hmacval)]:
        raise RuntimeError("HMAC is invalid")
    secret = hmac.new(key, b"Round secret:" + nonce, digestmod="sha256").digest()
    payload = bytearray(payload)
    for i in range(len(payload)):
        payload[i] = payload[i] ^ secret[i]
    s = BytesIO(payload)
    pin = compact.read_from(s)
    amount_in_cent = compact.read_from(s)
    return str(pin), amount_in_cent


@lnpos_lnurl_legacy_router.get("/{lnpos_id}")
async def lnurl_params(
    request: Request,
    lnpos_id: str,
    p: str = Query(None),
):
    lnpos = await get_lnpos(lnpos_id)
    if not lnpos:
        raise HTTPException(HTTPStatus.NOT_FOUND, detail="lnpos not found.")

    if len(p) % 4 > 0:
        p += "=" * (4 - (len(p) % 4))

    data = base64.urlsafe_b64decode(p)
    try:
        pin, amount_in_cent = xor_decrypt(lnpos.key.encode(), data)
    except Exception as exc:
        raise HTTPException(
            HTTPStatus.BAD_REQUEST, detail=f"decryption error: {exc!s}"
        ) from exc

    price_sat = (
        await fiat_amount_as_satoshis(float(amount_in_cent) / 100, lnpos.currency)
        if lnpos.currency != "sat"
        else amount_in_cent
    )
    if price_sat is None:
        raise HTTPException(HTTPStatus.BAD_REQUEST, detail="Price fetch error.")

    price_sat = int(price_sat * ((lnpos.profit / 100) + 1))
    price_msat = price_sat * 1000

    lnpos_payment = LnposPayment(
        id=urlsafe_short_hash(),
        lnpos_id=lnpos.id,
        sats=price_sat,
        pin=int(pin),
    )
    await create_lnpos_payment(lnpos_payment)
    return {
        "tag": "payRequest",
        "callback": str(
            request.url_for("lnpos.lnurl_callback", payment_id=lnpos_payment.id)
        ),
        "minSendable": price_msat,
        "maxSendable": price_msat,
        "metadata": lnpos.lnurlpay_metadata,
    }


@lnpos_lnurl_legacy_router.get(
    "/cb/{payment_id}",
    status_code=HTTPStatus.OK,
    name="lnpos.lnurl_legacy_callback",
)
async def lnurl_legacy_callback(request: Request, payment_id: str):
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
