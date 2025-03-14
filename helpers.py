import hmac
from io import BytesIO

from embit import compact


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
