from base64 import urlsafe_b64decode

from Cryptodome.Cipher import AES


def aes_decrypt(key: str, iv: str, ciphertext: str) -> str:
    _iv = urlsafe_b64decode(iv + "=" * (4 - len(iv) % 4))
    _ct = urlsafe_b64decode(ciphertext + "=" * (4 - len(ciphertext) % 4))
    cipher = AES.new(key.encode(), AES.MODE_CBC, _iv)
    pt = cipher.decrypt(_ct)
    return pt.split(b"\x00")[0].decode()
