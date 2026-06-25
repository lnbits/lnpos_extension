from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from lnbits.core.crud import get_standalone_payment, get_user
from lnbits.core.models import WalletTypeInfo
from lnbits.decorators import (
    require_admin_key,
    require_invoice_key,
)

from .crud import (
    create_lnpos,
    delete_lnpos,
    get_lnpos,
    get_lnpos_payment,
    get_lnposs,
    update_lnpos,
)
from .models import CreateLnpos

lnpos_api_router = APIRouter()


@lnpos_api_router.post("/api/v1", dependencies=[Depends(require_admin_key)])
async def api_lnpos_create(data: CreateLnpos):
    return await create_lnpos(data)


@lnpos_api_router.put("/api/v1/{lnpos_id}", dependencies=[Depends(require_admin_key)])
async def api_lnpos_update(data: CreateLnpos, lnpos_id: str):
    lnpos = await get_lnpos(lnpos_id)
    if not lnpos:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="lnpos does not exist"
        )
    for field, value in data.dict().items():
        setattr(lnpos, field, value)
    return await update_lnpos(lnpos)


@lnpos_api_router.get("/api/v1")
async def api_lnposs_get(wallet: WalletTypeInfo = Depends(require_invoice_key)):
    user = await get_user(wallet.wallet.user)
    assert user, "Lnpos cannot retrieve user"
    return await get_lnposs(user.wallet_ids)


@lnpos_api_router.get("/api/v1/{lnpos_id}", dependencies=[Depends(require_invoice_key)])
async def api_lnpos_get(lnpos_id: str):
    lnpos = await get_lnpos(lnpos_id)
    if not lnpos:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="LNPoS does not exist"
        )
    return lnpos


@lnpos_api_router.delete(
    "/api/v1/{lnpos_id}", dependencies=[Depends(require_admin_key)]
)
async def api_lnpos_delete(lnpos_id: str):
    lnpos = await get_lnpos(lnpos_id)
    if not lnpos:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="LNPoS does not exist."
        )

    await delete_lnpos(lnpos_id)


@lnpos_api_router.get("/api/v1/payment/{payment_id}")
async def api_lnpos_payment_get(payment_id: str):
    lnpos_payment = await get_lnpos_payment(payment_id)
    if not lnpos_payment:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="No lnpos payment")
    if not lnpos_payment.payment_hash:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Payment hash of lnpos_payment is missing.",
        )
    payment = await get_standalone_payment(lnpos_payment.payment_hash)
    if not payment:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Payment not found."
        )
    return {
        "paid": payment.success,
        "pin": lnpos_payment.pin if payment.success else None,
    }
