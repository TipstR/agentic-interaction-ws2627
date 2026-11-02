"""Configuration: read .env at start-up, real environment variables take precedence."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED = ("OPENAI_BASE_URL", "OPENAI_API_KEY", "MODEL", "DATA_BASE_URL")


@dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str
    model: str
    data_base_url: str


def load_config() -> Config:
    # override=False: variables already set in the environment win over .env.
    # utf-8-sig: tolerate a byte-order mark that some Windows editors add.
    load_dotenv(REPO_ROOT / ".env", override=False, encoding="utf-8-sig")

    missing = [name for name in REQUIRED if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing configuration: {', '.join(missing)} (set them in .env)")

    return Config(
        base_url=os.environ["OPENAI_BASE_URL"],
        api_key=os.environ["OPENAI_API_KEY"],
        model=os.environ["MODEL"],
        data_base_url=os.environ["DATA_BASE_URL"].rstrip("/"),
    )
