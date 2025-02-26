from typing import Callable

import consts as cst
import pytest
from algokit_utils import (
    AlgorandClient,
    AssetOptInParams,
    AssetTransferParams,
    LogicError,
    PaymentParams,
    SendParams,
    SigningAccount,
)
from algosdk.error import AlgodHTTPError

import smart_contracts.digital_marketplace.errors as err
from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    BidArgs,
    DepositArgs,
    DigitalMarketplaceClient,
    OpenSaleArgs,
    SaleKey,
)


@pytest.fixture(scope="function")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient, first_bidder: SigningAccount
) -> DigitalMarketplaceClient:
    return digital_marketplace_client.clone(default_sender=first_bidder.address)


def test_pass_noop_claim_unencumbered_bids(
    dm_client: DigitalMarketplaceClient,
    scenario_bid: Callable,
    seller: SigningAccount,
    first_bidder: SigningAccount,
    asset_to_sell: int,
) -> None:
    placed_bids_before_call = dm_client.state.box.placed_bids.get_value(first_bidder.address)
    deposited_before_call = dm_client.state.local_state(first_bidder.address).deposited

    dm_client.send.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    assert (
        dm_client.state.box.placed_bids.get_value(first_bidder.address)
        == placed_bids_before_call
    )
    assert (
        dm_client.state.local_state(first_bidder.address).deposited - deposited_before_call
        == 0
    )
