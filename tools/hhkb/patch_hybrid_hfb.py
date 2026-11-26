#!/usr/bin/env python3
"""Replace the STM32 application in a verified Hybrid ANSI update."""
import argparse
import hashlib
import struct
from pathlib import Path

STOCK_FILENAME = "HHKB800_FW_A048.hfb"
STOCK_SHA256 = "635b995eb5a15aa50c2cedc60da7d8998fcca8285a09d41d984c07fffcaf9d43"
BANK_SIZE = 0x10000
NRF_IMAGE_SIZE = 0x35000
MODEL = b"AHUX01"
VERSION = bytes([0x0A, 0x00, 0x05, 0x00])  # A0.50


def compute_crc16_mcrf4xx(data: bytes) -> int:
    """CRC-16/MCRF4XX (reflected poly 0x8408, init 0xFFFF, no final XOR)."""
    crc = 0xFFFF
    for b in data:
        cur = (crc ^ b) & 0xFF
        for _ in range(8):
            cur = (cur >> 1) ^ 0x8408 if cur & 1 else cur >> 1
        crc = (crc >> 8) ^ cur
    return crc


def bank_payload(application: bytes) -> bytes:
    if not 8 <= len(application) <= BANK_SIZE:
        raise ValueError("STM32 application must fit in 64 KiB")
    stack, reset = struct.unpack_from("<II", application)
    if not (0x20000000 < stack <= 0x20005000 and stack % 8 == 0
            and reset & 1 and 0x08010008 <= (reset & ~1) < 0x08010000 + len(application)):
        raise ValueError("invalid STM32 Bank 2 vector table")
    return application.ljust(BANK_SIZE, b"\xff")


def assemble(payload: bytes, tail: bytes) -> bytes:
    prefix_crc = struct.pack("<H", compute_crc16_mcrf4xx(payload))
    body = prefix_crc + payload + tail
    return struct.pack("<H", compute_crc16_mcrf4xx(body)) + body


def patch(stock: bytes, application: bytes) -> bytes:
    if hashlib.sha256(stock).hexdigest() != STOCK_SHA256:
        raise ValueError(f"expected the official {STOCK_FILENAME} template")
    tail = bytearray(stock[4 + BANK_SIZE:])
    tail[-10:-6] = VERSION
    return assemble(bank_payload(application), bytes(tail))


def make_stm32_only(application: bytes) -> bytes:
    """Build an experimental Hybrid container with an nRF image meant to be rejected."""
    blank_radio = b"\xff" * NRF_IMAGE_SIZE
    invalid_digest = bytes(16)
    if hashlib.md5(blank_radio).digest() == invalid_digest:
        raise ValueError("blank radio image must fail the Nordic integrity check")
    # The last 14 bytes of the nRF image also begin the HFB footer.
    tail = b"\xff" * 12 + invalid_digest + blank_radio
    tail += MODEL + VERSION + b"\xff" * 6
    return assemble(bank_payload(application), tail)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("application", type=Path)
    parser.add_argument("stock", type=Path, nargs="?")
    parser.add_argument("output", type=Path)
    parser.add_argument("--stm32-only", action="store_true",
                        help="generate a Hybrid HFB with an intentionally invalid blank nRF image")
    args = parser.parse_args()
    if args.output.suffix.lower() != ".hfb":
        parser.error("output must have an .hfb extension")
    if args.stm32_only == (args.stock is not None):
        parser.error("provide a factory template or use --stm32-only")
    try:
        application = args.application.read_bytes()
        if args.stm32_only:
            output = make_stm32_only(application)
        else:
            output = patch(args.stock.read_bytes(), application)
        with args.output.open("xb") as stream:
            stream.write(output)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
