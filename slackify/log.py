from datetime import datetime


def ok(msg: str):
    print(f"[{datetime.now()}] \033[1;32m[OK  ]\033[0m {msg}")

def info(msg: str):
    print(f"[{datetime.now()}] \033[1;34m[INFO]\033[0m {msg}")

def warn(msg: str):
    print(f"[{datetime.now()}] \033[1;33m[WARN]\033[0m {msg}")

def err(msg: str):
    print(f"[{datetime.now()}] \033[1;31m[ERR ]\033[0m {msg}")
