from typing import Callable

import consts as cst
import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    PaymentParams,
    SendParams,
    SigningAccount,
)
from algosdk.error import AlgodHTTPError

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    AcceptBidArgs,
    BidArgs,
    BuyArgs,
    DepositArgs,
    DigitalMarketplaceClient,
    SaleKey,
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
    receipt_book_before_call = dm_client.state.box.receipt_book.get_value(
        first_bidder.address
    )
    deposited_before_call = dm_client.state.local_state(first_bidder.address).deposited

    dm_client.send.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    assert (
        dm_client.state.box.receipt_book.get_value(first_bidder.address)
        == receipt_book_before_call
    )
    assert (
        dm_client.state.local_state(first_bidder.address).deposited
        - deposited_before_call
        == 0
    )


def test_pass_opt_in_zero_claim_unencumbered_bids(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_first_bidder_bid: Callable,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    dm_client.send.clear_state()

    receipt_book_before_call = dm_client.state.box.receipt_book.get_value(
        first_bidder.address
    )

    dm_client.send.opt_in.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    assert (
        dm_client.state.box.receipt_book.get_value(first_bidder.address)
        == receipt_book_before_call
    )
    assert dm_client.state.local_state(first_bidder.address).deposited == 0


def test_pass_noop_positive_to_empty_claim_unencumbered_bids(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_second_bidder_outbid: Callable,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    assert dm_client.state.box.receipt_book.get_value(first_bidder.address) == [
        [[first_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo]
    ]
    deposited_before_call = dm_client.state.local_state(first_bidder.address).deposited

    dm_client.send.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.receipt_book.get_value(first_bidder.address)
    assert (
        dm_client.state.local_state(first_bidder.address).deposited
        - deposited_before_call
        == (cst.AMOUNT_TO_BID + cst.RECEIPT_BOOK_BOX_MBR).micro_algo
    )


def test_pass_opt_in_positive_to_empty_claim_unencumbered_bids(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_second_bidder_outbid: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    # Even a cleared account can later opt_in with claim_unencumbered bids
    #  to claim back any bid, but they will still lose their deposit.
    dm_client.new_group().deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=first_bidder.address,
                    receiver=dm_client.app_address,
                    amount=AlgoAmount(algo=1),
                )
            )
        )
    ).clear_state().send()

    assert dm_client.state.box.receipt_book.get_value(first_bidder.address) == [
        [[first_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo]
    ]

    dm_client.send.opt_in.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.receipt_book.get_value(first_bidder.address)
    assert (
        dm_client.state.local_state(first_bidder.address).deposited
        == (cst.AMOUNT_TO_BID + cst.RECEIPT_BOOK_BOX_MBR).micro_algo
    )


def test_pass_noop_positive_to_non_empty_claim_unencumbered_bids(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_second_bidder_outbid: Callable,
    first_seller: SigningAccount,
    second_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    dm_client.send.bid(
        BidArgs(
            sale_key=SaleKey(owner=second_seller.address, asset=asset_to_sell),
            new_bid_amount=cst.AMOUNT_TO_BID.micro_algo,
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )

    assert dm_client.state.box.receipt_book.get_value(first_bidder.address) == [
        [[first_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo],
        [[second_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo],
    ]
    deposited_before_call = dm_client.state.local_state(first_bidder.address).deposited

    dm_client.send.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    assert dm_client.state.box.receipt_book.get_value(first_bidder.address) == [
        [[second_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo]
    ]
    assert (
        dm_client.state.local_state(first_bidder.address).deposited
        - deposited_before_call
        == cst.AMOUNT_TO_BID.micro_algo
    )


def test_pass_opt_in_positive_to_non_empty_claim_unencumbered_bids(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_second_bidder_outbid: Callable,
    first_seller: SigningAccount,
    second_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    dm_client.new_group().bid(
        BidArgs(
            sale_key=SaleKey(owner=second_seller.address, asset=asset_to_sell),
            new_bid_amount=cst.AMOUNT_TO_BID.micro_algo,
        ),
    ).clear_state().send(SendParams(populate_app_call_resources=True))

    assert dm_client.state.box.receipt_book.get_value(first_bidder.address) == [
        [[first_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo],
        [[second_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo],
    ]

    dm_client.send.opt_in.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    assert dm_client.state.box.receipt_book.get_value(first_bidder.address) == [
        [[second_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo]
    ]
    assert (
        dm_client.state.local_state(first_bidder.address).deposited
        == cst.AMOUNT_TO_BID.micro_algo
    )


def test_pass_bid_was_sold_to_empty(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_first_bidder_bid: Callable,
    first_seller: SigningAccount,
    buyer: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    sale_key = SaleKey(owner=first_seller.address, asset=asset_to_sell)
    dm_client.clone(default_sender=buyer.address).send.buy(
        BuyArgs(sale_key=sale_key),
        params=CommonAppCallParams(extra_fee=AlgoAmount(micro_algo=1_000)),
        send_params=SendParams(populate_app_call_resources=True),
    )

    deposited_before_call = dm_client.state.local_state(first_bidder.address).deposited

    dm_client.send.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    assert (
        dm_client.state.local_state(first_bidder.address).deposited
        - deposited_before_call
        == (cst.AMOUNT_TO_BID + cst.RECEIPT_BOOK_BOX_MBR).micro_algo
    )
    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.receipt_book.get_value(first_bidder.address)


def test_pass_bid_was_accepted_to_empty(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_first_bidder_bid: Callable,
    first_seller: SigningAccount,
    buyer: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    dm_client.clone(default_sender=first_seller.address).send.accept_bid(
        AcceptBidArgs(asset=asset_to_sell),
        params=CommonAppCallParams(extra_fee=AlgoAmount(micro_algo=1_000)),
        send_params=SendParams(populate_app_call_resources=True),
    )

    deposited_before_call = dm_client.state.local_state(first_bidder.address).deposited

    dm_client.send.claim_unencumbered_bids(
        send_params=SendParams(populate_app_call_resources=True)
    )

    assert (
        dm_client.state.local_state(first_bidder.address).deposited
        - deposited_before_call
        == (cst.AMOUNT_TO_BID + cst.RECEIPT_BOOK_BOX_MBR).micro_algo
    )
    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.receipt_book.get_value(first_bidder.address)
