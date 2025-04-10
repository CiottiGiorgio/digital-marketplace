from typing import Callable

import consts as cst
import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    SendParams,
    SigningAccount,
)
from algosdk.error import AlgodHTTPError

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    AcceptBidArgs,
    Bid,
    DigitalMarketplaceClient,
    SaleKey,
)
from tests.digital_marketplace.client import helpers
from tests.digital_marketplace.client.helpers import receipt_book_mbr


def test_pass_accept_bid(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_first_bidder_bid: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    """
    Test accepting a bid, ensuring the bid is processed correctly
    and the state is updated as expected.
    """
    sale_key = SaleKey(owner=first_seller.address, asset=asset_to_sell)

    assert dm_client.state.box.sales.get_value(sale_key).bid == Bid(
        bidder=first_bidder.address, amount=cst.AMOUNT_TO_BID.micro_algo
    )
    assert dm_client.state.box.receipt_book.get_value(first_bidder.public_key) == [
        [[sale_key.owner, sale_key.asset], cst.AMOUNT_TO_BID.micro_algo]
    ]
    deposited_before_call = dm_client.state.box.deposited.get_value(
        first_seller.address
    )
    asa_balance_before_call = helpers.asa_amount(
        algorand_client,
        first_bidder.address,
        asset_to_sell,
    )
    bidder_deposited_before_call = dm_client.state.box.deposited.get_value(
        first_bidder.address
    )

    dm_client.send.accept_bid(
        AcceptBidArgs(asset=asset_to_sell),
        params=CommonAppCallParams(extra_fee=AlgoAmount(micro_algo=1_000)),
        send_params=SendParams(populate_app_call_resources=True),
    )

    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.sales.get_value(sale_key)
    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.receipt_book.get_value(first_bidder.public_key)
    assert (
        dm_client.state.box.deposited.get_value(first_seller.address)
        - deposited_before_call
        == (cst.AMOUNT_TO_BID + cst.SALES_BOX_MBR).micro_algo
    )
    assert (
        helpers.asa_amount(
            algorand_client,
            first_bidder.address,
            asset_to_sell,
        )
        - asa_balance_before_call
        == cst.ASA_AMOUNT_TO_SELL
    )
    assert (
        dm_client.state.box.deposited.get_value(first_bidder.address)
        - bidder_deposited_before_call
        == receipt_book_mbr(1).micro_algo
    )


def test_pass_unencumbered_bid_survives(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_second_bidder_outbid: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
    second_bidder: SigningAccount,
) -> None:
    """
    Test that an unencumbered bid survives after accepting a bid, ensuring the state
    is updated correctly and the appropriate bid remains.
    """
    sale_key = SaleKey(owner=first_seller.address, asset=asset_to_sell)

    assert dm_client.state.box.receipt_book.get_value(first_bidder.public_key) == [
        [[sale_key.owner, sale_key.asset], cst.AMOUNT_TO_BID.micro_algo]
    ]
    assert dm_client.state.box.receipt_book.get_value(second_bidder.public_key) == [
        [[sale_key.owner, sale_key.asset], cst.AMOUNT_TO_BID.micro_algo + 1]
    ]
    first_bidder_deposited_before_call = dm_client.state.box.deposited.get_value(
        first_bidder.address
    )
    second_bidder_deposited_before_call = dm_client.state.box.deposited.get_value(
        second_bidder.address
    )

    dm_client.send.accept_bid(
        AcceptBidArgs(asset=asset_to_sell),
        params=CommonAppCallParams(extra_fee=AlgoAmount(micro_algo=1_000)),
        send_params=SendParams(populate_app_call_resources=True),
    )

    assert dm_client.state.box.receipt_book.get_value(first_bidder.public_key) == [
        [[sale_key.owner, sale_key.asset], cst.AMOUNT_TO_BID.micro_algo]
    ]
    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.receipt_book.get_value(second_bidder.public_key)
    assert (
        dm_client.state.box.deposited.get_value(first_bidder.address)
        - first_bidder_deposited_before_call
        == 0
    )
    assert (
        dm_client.state.box.deposited.get_value(second_bidder.address)
        - second_bidder_deposited_before_call
        == receipt_book_mbr(1).micro_algo
    )
