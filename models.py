import json

from lnurl.types import LnurlPayMetadata
from pydantic import BaseModel


class CreateLnpos(BaseModel):
    title: str
    wallet: str
    currency: str
    device: str
    profit: float


class Lnpos(BaseModel):
    id: str
    key: str
    title: str
    wallet: str
    profit: float
    currency: str
    device: str

    @property
    def lnurlpay_metadata(self) -> LnurlPayMetadata:
        return LnurlPayMetadata(json.dumps([["text/plain", self.title]]))


class LnposPayment(BaseModel):
    id: str
    lnpos_id: str
    payment_hash: str
    payload: str
    pin: int
    sats: int


class Lnurlencode(BaseModel):
    url: str
