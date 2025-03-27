from typing import Callable

import consts as cst
import pytest
from algokit_utils import (
    LogicError,
    SigningAccount,
)

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    DigitalMarketplaceClient,
    UnencumberedBidsReceipt,
)


@pytest.fixture(scope="function")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient, first_bidder: SigningAccount
) -> DigitalMarketplaceClient:
    return digital_marketplace_client.clone(default_sender=first_bidder.address)


def test_fail_no_bids(
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
) -> None:
    """
    Test that claiming unencumbered bids fails when there are no bids.
    """
    with pytest.raises(LogicError):
        dm_client.send.claim_unencumbered_bids()


def test_pass_no_unencumbered_bids(
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_first_bidder_bid: Callable,
) -> None:
    """
    Test that the total bids are correct when there are no unencumbered bids.
    """
    assert (
        dm_client.send.get_total_and_unencumbered_bids().abi_return
        == UnencumberedBidsReceipt(
            total_bids=cst.AMOUNT_TO_BID.micro_algo, unencumbered_bids=0
        )
    )


def test_pass_with_unencumbered_bids(
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_second_bidder_outbid: Callable,
) -> None:
    """
    Test that the total bids and unencumbered bids are correct when there are unencumbered bids.
    """
    assert (
        dm_client.send.get_total_and_unencumbered_bids().abi_return
        == UnencumberedBidsReceipt(
            total_bids=cst.AMOUNT_TO_BID.micro_algo,
            unencumbered_bids=cst.AMOUNT_TO_BID.micro_algo,
        )
    )
