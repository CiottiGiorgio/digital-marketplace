from typing import Callable

import consts as cst
import pytest
from algokit_utils import (
    AlgoAmount,
    CommonAppCallParams,
    LogicError,
    SendParams,
    SigningAccount,
)
from algosdk.error import AlgodHTTPError

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    BidArgs,
    BuyArgs,
    DigitalMarketplaceClient,
    SaleKey,
)
from tests.digital_marketplace.client.helpers import receipt_book_mbr


@pytest.fixture(scope="function")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient, first_bidder: SigningAccount
) -> DigitalMarketplaceClient:
    return digital_marketplace_client.clone(default_sender=first_bidder.address)


def test_pass_claim_with_no_unencumbered_bids(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_first_bidder_bid: Callable,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    """
    Test that claiming unencumbered bids with no unencumbered bids does not change the state.
    """
    receipt_book_before_call = dm_client.state.box.receipt_book.get_value(
        first_bidder.public_key
    )
    deposited_before_call = dm_client.state.box.deposited.get_value(
        first_bidder.address
    )

    dm_client.send.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    assert (
        dm_client.state.box.receipt_book.get_value(first_bidder.public_key)
        == receipt_book_before_call
    )
    assert (
        dm_client.state.box.deposited.get_value(first_bidder.address)
        - deposited_before_call
        == 0
    )


def test_pass_claim_with_unencumbered_bids(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_second_bidder_outbid: Callable,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    """
    Test that claiming unencumbered bids with existing unencumbered bids updates the state correctly.
    """
    assert dm_client.state.box.receipt_book.get_value(first_bidder.public_key) == [
        [[first_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo]
    ]
    deposited_before_call = dm_client.state.box.deposited.get_value(
        first_bidder.address
    )

    dm_client.send.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.receipt_book.get_value(first_bidder.public_key)
    assert (
        dm_client.state.box.deposited.get_value(first_bidder.address)
        - deposited_before_call
        == (cst.AMOUNT_TO_BID + receipt_book_mbr(1)).micro_algo
    )


def test_pass_claim_with_residue_encumbered_bids(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_second_bidder_outbid: Callable,
    first_seller: SigningAccount,
    second_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    """
    Test that claiming unencumbered bids with residue encumbered bids updates the state correctly.
    """
    dm_client.send.bid(
        BidArgs(
            sale_key=SaleKey(owner=second_seller.address, asset=asset_to_sell),
            new_bid_amount=cst.AMOUNT_TO_BID.micro_algo,
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )

    assert dm_client.state.box.receipt_book.get_value(first_bidder.public_key) == [
        [[first_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo],
        [[second_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo],
    ]
    deposited_before_call = dm_client.state.box.deposited.get_value(
        first_bidder.address
    )

    dm_client.send.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    assert dm_client.state.box.receipt_book.get_value(first_bidder.public_key) == [
        [[second_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo]
    ]
    assert (
        dm_client.state.box.deposited.get_value(first_bidder.address)
        - deposited_before_call
        == (cst.AMOUNT_TO_BID + cst.RECEIPT_BOOK_BOX_PER_RECEIPT_MBR).micro_algo
    )


def test_pass_bid_was_sold(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_first_bidder_bid: Callable,
    first_seller: SigningAccount,
    buyer: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    """
    Test that claiming unencumbered bids after the bid was sold updates the state correctly.
    """
    sale_key = SaleKey(owner=first_seller.address, asset=asset_to_sell)
    dm_client.clone(default_sender=buyer.address).send.buy(
        BuyArgs(sale_key=sale_key),
        params=CommonAppCallParams(extra_fee=AlgoAmount(micro_algo=1_000)),
        send_params=SendParams(populate_app_call_resources=True),
    )

    deposited_before_call = dm_client.state.box.deposited.get_value(
        first_bidder.address
    )

    dm_client.send.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    assert (
        dm_client.state.box.deposited.get_value(first_bidder.address)
        - deposited_before_call
        == (cst.AMOUNT_TO_BID + receipt_book_mbr(1)).micro_algo
    )
    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.receipt_book.get_value(first_bidder.public_key)


def test_fail_bid_was_accepted(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_accept_first_bid: Callable,
    first_seller: SigningAccount,
    buyer: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    """
    Test that claiming unencumbered bids fails if the bid was accepted.
    """
    with pytest.raises(LogicError, match=f"check self.{cst.RECEIPT_BOOK} entry exists"):
        dm_client.send.claim_unencumbered_bids(
            send_params=SendParams(populate_app_call_resources=True)
        )


def test_pass_reopened_sale_is_still_unencumbered(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_bid_buy_both_sales: Callable,
    scenario_open_sale: Callable,
    first_seller: SigningAccount,
    buyer: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    """
    Test that claiming unencumbered bids after reopening the same sale updates the state correctly.
    """
    assert dm_client.state.box.receipt_book.get_value(first_bidder.public_key) == [
        [[first_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo]
    ]
    deposited_before_call = dm_client.state.box.deposited.get_value(
        first_bidder.address
    )

    dm_client.send.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.receipt_book.get_value(first_bidder.public_key)
    assert (
        dm_client.state.box.deposited.get_value(first_bidder.address)
        - deposited_before_call
        == (cst.AMOUNT_TO_BID + receipt_book_mbr(1)).micro_algo
    )


def test_fail_empty_receipt_book(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    with pytest.raises(LogicError, match=f"check self.{cst.RECEIPT_BOOK} entry exists"):
        dm_client.send.claim_unencumbered_bids(
            send_params=SendParams(populate_app_call_resources=True)
        )
