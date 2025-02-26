from typing import Callable

import consts as cst
import pytest
from algokit_utils import (
    SendParams,
    SigningAccount,
)
from algosdk.error import AlgodHTTPError

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    DigitalMarketplaceClient,
)


@pytest.fixture(scope="function")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient, first_bidder: SigningAccount
) -> DigitalMarketplaceClient:
    return digital_marketplace_client.clone(default_sender=first_bidder.address)


def test_pass_noop_zero_claim_unencumbered_bids(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_first_bidder_bid: Callable,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    placed_bids_before_call = dm_client.state.box.placed_bids.get_value(
        first_bidder.address
    )
    deposited_before_call = dm_client.state.local_state(first_bidder.address).deposited

    dm_client.send.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    assert (
        dm_client.state.box.placed_bids.get_value(first_bidder.address)
        == placed_bids_before_call
    )
    assert (
        dm_client.state.local_state(first_bidder.address).deposited
        - deposited_before_call
        == 0
    )


def test_pass_noop_positive_to_empty_claim_unencumbered_bids(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_second_bidder_outbid: Callable,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    assert dm_client.state.box.placed_bids.get_value(first_bidder.address) == [
        [[first_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo]
    ]
    deposited_before_call = dm_client.state.local_state(first_bidder.address).deposited

    dm_client.send.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.placed_bids.get_value(first_bidder.address)
    assert (
        dm_client.state.local_state(first_bidder.address).deposited
        - deposited_before_call
        == (cst.AMOUNT_TO_BID + cst.PLACED_BIDS_BOX_MBR).micro_algo
    )


def test_pass_opt_in_positive_to_empty_claim_unencumbered_bids(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_second_bidder_outbid: Callable,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    dm_client.send.clear_state()

    assert dm_client.state.box.placed_bids.get_value(first_bidder.address) == [
        [[first_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo]
    ]

    dm_client.send.opt_in.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.placed_bids.get_value(first_bidder.address)
    assert (
        dm_client.state.local_state(first_bidder.address).deposited
        == (cst.AMOUNT_TO_BID + cst.PLACED_BIDS_BOX_MBR).micro_algo
    )


def test_pass_noop_positive_to_non_empty_claim_unencumbered_bids(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_second_bidder_outbid: Callable,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    assert dm_client.state.box.placed_bids.get_value(first_bidder.address) == [
        [[first_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo]
    ]
    deposited_before_call = dm_client.state.local_state(first_bidder.address).deposited

    dm_client.send.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.placed_bids.get_value(first_bidder.address)
    assert (
        dm_client.state.local_state(first_bidder.address).deposited
        - deposited_before_call
        == (cst.AMOUNT_TO_BID + cst.PLACED_BIDS_BOX_MBR).micro_algo
    )


def test_pass_opt_in_positive_to_non_empty_claim_unencumbered_bids(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_second_bidder_outbid: Callable,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    dm_client.send.clear_state()

    assert dm_client.state.box.placed_bids.get_value(first_bidder.address) == [
        [[first_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo]
    ]

    dm_client.send.opt_in.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.placed_bids.get_value(first_bidder.address)
    assert (
        dm_client.state.local_state(first_bidder.address).deposited
        == (cst.AMOUNT_TO_BID + cst.PLACED_BIDS_BOX_MBR).micro_algo
    )
