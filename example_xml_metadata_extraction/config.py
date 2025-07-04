import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LWE_CONFIG_DIR = BASE_DIR / "lwe" / "config"
LWE_DATA_DIR = BASE_DIR / "lwe" / "data"


def set_environment_variables() -> None:
    os.environ["LWE_CONFIG_DIR"] = str(LWE_CONFIG_DIR)
    os.environ["LWE_DATA_DIR"] = str(LWE_DATA_DIR)
