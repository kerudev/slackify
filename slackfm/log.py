from datetime import datetime


def __log(fmt: str, msg: str) -> None:
    print(f"[{datetime.now()}] {fmt}\033[0m {msg}")

def ok(msg: str) -> None:
    __log("\033[1;32m[OK  ]", msg)

def info(msg: str) -> None:
    __log("\033[1;34m[INFO]", msg)

def warn(msg: str) -> None:
    __log("\033[1;33m[WARN]", msg)

def err(msg: str) -> None:
    __log("\033[1;31m[ERR ]", msg)
