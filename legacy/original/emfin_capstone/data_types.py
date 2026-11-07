from enum import Enum


class Exchange(Enum):
    """A real trading venue.

    This models *where* an instrument trades and nothing else.  It is
    deliberately narrow: cash, crypto and non-market custom holdings have no
    venue and are represented by ``AssetType`` with ``Asset.exchange = None``,
    not by a pseudo-member here.  Vendor formats that cram
    asset class or cash/custom semantics into a single "exchange" column are
    decomposed at their reader boundary, never propagated into this type.

    The member value is the canonical venue code.
    """

    NYSE_ARCA = "NYSE ARCA"
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    US = "US"
    HK = "HK"
    SHE = "SHE"


class AssetType(Enum):
    EQUITY = "EQUITY"
    FIXED_INCOME = "FIXED_INCOME"
    REAL_ESTATE = "REAL_ESTATE"
    CRYPTO = "CRYPTO"
    CASH = "CASH"
    DEPOSIT = "DEPOSIT"

