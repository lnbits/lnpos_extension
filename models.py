import json

from lnurl.types import LnurlPayMetadata
from pydantic import BaseModel


class CreateLnpos(BaseModel):
    title: str
    wallet: str
    currency: str | None = "sat"
    profit: float | None = None


class Lnpos(BaseModel):
    id: str
    key: str
    title: str
    wallet: str
    profit: float
    currency: str

    @property
    def lnurlpay_metadata(self) -> LnurlPayMetadata:
        return LnurlPayMetadata(json.dumps([["text/plain", self.title]]))


class LnposPayment(BaseModel):
    id: str
    lnpos_id: str
    pin: int
    sats: int
    amount: float | None = None
    payment_hash: str | None = None
