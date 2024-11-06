from http import HTTPStatus

import bolt11
import httpx
from fastapi import APIRouter, Depends, HTTPException
from lnbits.core.crud import get_user, get_wallet
from lnbits.core.models import WalletTypeInfo
from lnbits.core.services import pay_invoice
from lnbits.core.views.api import api_lnurlscan
from lnbits.decorators import (
    check_user_extension_access,
    require_admin_key,
    require_invoice_key,
)
from lnbits.settings import settings
from lnbits.utils.exchange_rates import currencies
from lnurl import encode as lnurl_encode
from loguru import logger

from .crud import (
    create_lnpos,
    delete_atm_payment_link,
    delete_lnpos,
    get_lnpos,
    get_lnpos_payment,
    get_lnpos_payments,
    get_lnposs,
    update_lnpos,
    update_lnpos_payment,
)
from .helpers import register_atm_payment
from .models import CreateLnpos, Lnurlencode

lnpos_api_router = APIRouter()


@lnpos_api_router.get("/api/v1/currencies")
async def api_list_currencies_available():
    return list(currencies.keys())


@lnpos_api_router.post("/api/v1/lnurlpos", dependencies=[Depends(require_admin_key)])
async def api_lnpos_create(data: CreateLnpos):
    return await create_lnpos(data)


@lnpos_api_router.put(
    "/api/v1/lnurlpos/{lnpos_id}", dependencies=[Depends(require_admin_key)]
)
async def api_lnpos_update(data: CreateLnpos, lnpos_id: str):
    lnpos = await get_lnpos(lnpos_id)
    if not lnpos:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="lnpos does not exist"
        )
    for field, value in data.dict().items():
        setattr(lnpos, field, value)
    return await update_lnpos(lnpos)


@lnpos_api_router.get("/api/v1/lnurlpos")
async def api_lnposs_retrieve(wallet: WalletTypeInfo = Depends(require_invoice_key)):
    user = await get_user(wallet.wallet.user)
    assert user, "Lnpos cannot retrieve user"
    return await get_lnposs(user.wallet_ids)


@lnpos_api_router.get(
    "/api/v1/lnurlpos/{lnpos_id}", dependencies=[Depends(require_invoice_key)]
)
async def api_lnpos_retrieve(lnpos_id: str):
    lnpos = await get_lnpos(lnpos_id)
    if not lnpos:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="lnpos does not exist"
        )
    return lnpos


@lnpos_api_router.delete(
    "/api/v1/lnurlpos/{lnpos_id}", dependencies=[Depends(require_admin_key)]
)
async def api_lnpos_delete(lnpos_id: str):
    lnpos = await get_lnpos(lnpos_id)
    if not lnpos:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Lnpos does not exist."
        )

    await delete_lnpos(lnpos_id)


#########ATM API#########


@lnpos_api_router.get("/api/v1/atm")
async def api_atm_payments_retrieve(
    wallet: WalletTypeInfo = Depends(require_invoice_key),
):
    user = await get_user(wallet.wallet.user)
    assert user, "Lnpos cannot retrieve user"
    lnposs = await get_lnposs(user.wallet_ids)
    deviceids = []
    for lnpos in lnposs:
        if lnpos.device == "atm":
            deviceids.append(lnpos.id)
    return await get_lnpos_payments(deviceids)


@lnpos_api_router.post(
    "/api/v1/lnurlencode", dependencies=[Depends(require_invoice_key)]
)
async def api_lnurlencode(data: Lnurlencode):
    lnurl = lnurl_encode(data.url)
    logger.debug(lnurl)
    if not lnurl:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Lnurl could not be encoded."
        )
    return lnurl


@lnpos_api_router.delete(
    "/api/v1/atm/{atm_id}", dependencies=[Depends(require_admin_key)]
)
async def api_atm_payment_delete(atm_id: str):
    lnpos = await get_lnpos_payment(atm_id)
    if not lnpos:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="ATM payment does not exist."
        )

    await delete_atm_payment_link(atm_id)


@lnpos_api_router.get("/api/v1/ln/{lnpos_id}/{p}/{ln}")
async def get_lnpos_payment_lightning(lnpos_id: str, p: str, ln: str) -> str:
    """
    Handle Lightning payments for atms via invoice, lnaddress, lnurlp.
    """
    ln = ln.strip().lower()

    lnpos = await get_lnpos(lnpos_id)
    if not lnpos:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="lnpos does not exist"
        )

    wallet = await get_wallet(lnpos.wallet)
    if not wallet:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Wallet does not exist connected to atm, payment could not be made",
        )
    lnpos_payment, price_msat = await register_atm_payment(lnpos, p)
    if not lnpos_payment:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Payment already claimed."
        )

    # If its an lnaddress or lnurlp get the request from callback
    elif ln[:5] == "lnurl" or "@" in ln and "." in ln.split("@")[-1]:
        data = await api_lnurlscan(ln)
        logger.debug(data)
        if data.get("status") == "ERROR":
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail=data.get("reason")
            )
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url=f"{data['callback']}?amount={lnpos_payment.sats * 1000}"
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail="Could not get callback from lnurl",
                )
            ln = response.json()["pr"]

    # If just an invoice
    elif ln[:4] == "lnbc":
        ln = ln

    # If ln is gibberish, return an error
    else:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="""
            Wrong format for payment, could not be made.
            Use LNaddress or LNURLp
            """,
        )

    # If its an invoice check its a legit invoice
    if ln[:4] == "lnbc":
        invoice = bolt11.decode(ln)
        assert invoice.amount_msat, "Amountless invoices are not allowed"
        if not invoice.payment_hash:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN, detail="Not valid payment request"
            )
        if not invoice.payment_hash:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN, detail="Not valid payment request"
            )
        if int(invoice.amount_msat / 1000) != lnpos_payment.sats:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail="Request is not the same as withdraw amount",
            )

    # Finally log the payment and make the payment
    try:
        lnpos_payment, price_msat = await register_atm_payment(lnpos, p)
        assert lnpos_payment
        lnpos_payment.payment_hash = lnpos_payment.payload
        await update_lnpos_payment(lnpos_payment)
        if ln[:4] == "lnbc":
            await pay_invoice(
                wallet_id=lnpos.wallet,
                payment_request=ln,
                max_sat=price_msat,
                extra={"tag": "lnpos", "id": lnpos_payment.id},
            )
    except Exception as exc:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=f"{exc!s}"
        ) from exc

    return lnpos_payment.id


@lnpos_api_router.get("/api/v1/boltz/{lnpos_id}/{payload}/{onchain_liquid}/{address}")
async def get_lnpos_payment_boltz(
    lnpos_id: str, payload: str, onchain_liquid: str, address: str
):
    """
    Handle Boltz payments for atms.
    """
    lnpos = await get_lnpos(lnpos_id)
    if not lnpos:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="lnpos does not exist"
        )

    lnpos_payment, _ = await register_atm_payment(lnpos, payload)
    assert lnpos_payment
    if lnpos_payment == "ERROR":
        return lnpos_payment
    if lnpos_payment.payload == lnpos_payment.payment_hash:
        return {"status": "ERROR", "reason": "Payment already claimed."}
    if lnpos_payment.payment_hash == "pending":
        return {
            "status": "ERROR",
            "reason": "Pending. If you are unable to withdraw contact vendor",
        }
    wallet = await get_wallet(lnpos.wallet)
    if not wallet:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Wallet does not exist connected to atm, payment could not be made",
        )
    access = await check_user_extension_access(wallet.user, "boltz")
    if not access.success:
        return {"status": "ERROR", "reason": "Boltz not enabled"}

    data = {
        "wallet": lnpos.wallet,
        "asset": onchain_liquid.replace("temp", "/"),
        "amount": lnpos_payment.sats,
        "direction": "send",
        "instant_settlement": True,
        "onchain_address": address,
        "feerate": False,
        "feerate_value": 0,
    }

    try:
        lnpos_payment.payload = payload
        lnpos_payment.payment_hash = "pending"
        lnpos_payment_updated = await update_lnpos_payment(lnpos_payment)
        assert lnpos_payment_updated
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url=f"http://{settings.host}:{settings.port}/boltz/api/v1/swap/reverse",
                headers={"X-API-KEY": wallet.adminkey},
                json=data,
            )
            lnpos_payment.payment_hash = lnpos_payment.payload
            lnpos_payment_updated = await update_lnpos_payment(lnpos_payment)
            assert lnpos_payment_updated
            resp = response.json()
            return resp
    except Exception as exc:
        lnpos_payment.payment_hash = "payment_hash"
        lnpos_payment_updated = await update_lnpos_payment(lnpos_payment)
        assert lnpos_payment_updated
        return {"status": "ERROR", "reason": str(exc)}
