"""
Decrypt SCS Software's "ScsC" container format (used to wrap ETS2/ATS save files
regardless of g_save_format).

Algorithm and constants taken from the header struct and decrypt routine in
TheLazyTomcat/SII_Decrypt (Source/SII_Decrypt_Decryptor.pas), MPL-2.0 licensed. That
project's own comment attributes the AES key to a "Savegame Decrypter" utility publicly
posted on the SCS forum in 2013 (forum.scssoft.com/viewtopic.php?f=34&t=164103#p280580) --
this is a long-public, community-standard constant, not a secret or a crack.

Header layout (56 bytes, all little-endian):
    signature   4 bytes   b"ScsC"
    hmac        32 bytes  (unused here -- not verified on decrypt)
    iv          16 bytes  AES-CBC initialization vector
    data_size   4 bytes   size of the decompressed payload
followed by the AES-256-CBC ciphertext, which decrypts to a zlib-compressed blob of
exactly `data_size` bytes once inflated.

Writing does NOT need the reverse of this -- see Milestone 0 in docs/design-decisions.md:
the game accepts a raw, unwrapped plain-text (SiiNunit) save file directly. This module is
only needed to read an existing real save.
"""

import struct
import zlib

from Crypto.Cipher import AES

SCSC_MAGIC = b"ScsC"

SII_KEY = bytes((
    0x2a, 0x5f, 0xcb, 0x17, 0x91, 0xd2, 0x2f, 0xb6, 0x02, 0x45, 0xb3, 0xd8, 0x36, 0x9e, 0xd0, 0xb2,
    0xc2, 0x73, 0x71, 0x56, 0x3f, 0xbf, 0x1f, 0x3c, 0x9e, 0xdf, 0x6b, 0x11, 0x82, 0x5a, 0x5d, 0x0a,
))

_HEADER_FMT = "<4s32s16sI"
_HEADER_SIZE = struct.calcsize(_HEADER_FMT)
assert _HEADER_SIZE == 56


def is_encrypted(data: bytes) -> bool:
    return data[:4] == SCSC_MAGIC


def decrypt(data: bytes) -> bytes:
    """Return the decompressed inner SII content (starts with b'SiiNunit' if text)."""
    if not is_encrypted(data):
        raise ValueError(f"Not a ScsC container (magic: {data[:4]!r})")

    _signature, _hmac, iv, data_size = struct.unpack(_HEADER_FMT, data[:_HEADER_SIZE])
    ciphertext = data[_HEADER_SIZE:]

    cipher = AES.new(SII_KEY, AES.MODE_CBC, iv)
    compressed = cipher.decrypt(ciphertext)

    return zlib.decompress(compressed)[:data_size]
