from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from lnbits.core.crud import (
    get_standalone_payment,
)
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer

from .crud import get_lnpos, get_lnpos_payment

lnpos_generic_router = APIRouter()


def lnpos_renderer():
    return template_renderer(["lnpos/templates"])


@lnpos_generic_router.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(check_user_exists)):
    return lnpos_renderer().TemplateResponse(
        "lnpos/index.html",
        {"request": request, "user": user.json()},
    )


@lnpos_generic_router.get(
    "/{payment_id}", name="lnpos.displaypin", response_class=HTMLResponse
)
async def displaypin(request: Request, payment_id: str):
    lnpos_payment = await get_lnpos_payment(payment_id)
    if not lnpos_payment:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="No lnpos payment")
    device = await get_lnpos(lnpos_payment.lnpos_id)
    if not device:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="lnpos not found.")
    if not lnpos_payment.payment_hash:
        raise HTTPException(
            HTTPStatus.NOT_FOUND, "Payment_hash of lnpos_payment is missing."
        )
    payment = await get_standalone_payment(lnpos_payment.payment_hash)
    if not payment:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Payment not found."
        )
    status = await payment.check_status()
    if status.success:
        return lnpos_renderer().TemplateResponse(
            "lnpos/paid.html", {"request": request, "pin": lnpos_payment.pin}
        )
    return lnpos_renderer().TemplateResponse(
        "lnpos/error.html",
        {"request": request, "pin": "filler", "not_paid": True},
    )
