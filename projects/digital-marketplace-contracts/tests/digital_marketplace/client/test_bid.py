from typing import Callable

import consts as cst
import pytest
from algokit_utils import (
    SendParams,
    SigningAccount,
)

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    BidArgs,
    DigitalMarketplaceClient,
    SaleKey,
)


@pytest.fixture(scope="function")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient, bidder: SigningAccount
) -> DigitalMarketplaceClient:
    return digital_marketplace_client.clone(default_sender=bidder.address)


def test_pass_bid(
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    seller: SigningAccount,
    asset_to_sell: int,
) -> None:
    dm_client.send.bid(
        BidArgs(
            sale_key=SaleKey(owner=seller.address, asset=asset_to_sell),
            new_bid_amount=cst.AMOUNT_TO_BID,
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )
