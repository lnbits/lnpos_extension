from Cryptodome.Cipher import AES


def aes_decrypt(key: str, iv: str, ciphertext: str) -> str:
    _iv = bytes.fromhex(iv)
    _ct = bytes.fromhex(ciphertext)
    cipher = AES.new(key.encode(), AES.MODE_CBC, _iv)
    pt = cipher.decrypt(_ct)
    return pt.split(b"\x00")[0].decode()
