from typing import Callable

import consts as cst
import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    LogicError,
    SendParams,
    SigningAccount,
)
from algosdk.error import AlgodHTTPError

import smart_contracts.digital_marketplace.errors as err
from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    BidArgs,
    DigitalMarketplaceClient,
    SaleKey,
    WithdrawArgs,
)


@pytest.fixture(scope="function")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient, first_bidder: SigningAccount
) -> DigitalMarketplaceClient:
    return digital_marketplace_client.clone(default_sender=first_bidder.address)


def test_pass_first_placed_bid_is_first_bid(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    sale_key = SaleKey(owner=first_seller.address, asset=asset_to_sell)
    assert dm_client.state.box.sales.get_value(sale_key).bid == []
    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.placed_bids.get_value(first_bidder.address)
    deposited_before_call = dm_client.state.local_state(first_bidder.address).deposited

    dm_client.send.bid(
        BidArgs(
            sale_key=sale_key,
            new_bid_amount=cst.AMOUNT_TO_BID.micro_algo,
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )

    assert dm_client.state.box.sales.get_value(sale_key).bid == [
        [first_bidder.address, cst.AMOUNT_TO_BID.micro_algo]
    ]
    assert dm_client.state.box.placed_bids.get_value(first_bidder.address) == [
        [
            [first_seller.address, asset_to_sell],
            cst.AMOUNT_TO_BID.micro_algo,
        ]
    ]
    assert (
        dm_client.state.local_state(first_bidder.address).deposited
        - deposited_before_call
        == -(cst.PLACED_BIDS_BOX_MBR + cst.AMOUNT_TO_BID).micro_algo
    )


def test_pass_first_placed_bid_is_outbid(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_first_bidder_bid: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
    second_bidder: SigningAccount,
) -> None:
    sale_key = SaleKey(owner=first_seller.address, asset=asset_to_sell)
    assert dm_client.state.box.sales.get_value(sale_key).bid == [
        [first_bidder.address, cst.AMOUNT_TO_BID.micro_algo]
    ]
    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.placed_bids.get_value(second_bidder.address)
    deposited_before_call = dm_client.state.local_state(second_bidder.address).deposited

    dm_client.clone(default_sender=second_bidder.address).send.bid(
        BidArgs(
            sale_key=sale_key,
            new_bid_amount=cst.AMOUNT_TO_OUTBID.micro_algo,
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )

    assert dm_client.state.box.sales.get_value(sale_key).bid == [
        [second_bidder.address, cst.AMOUNT_TO_OUTBID.micro_algo]
    ]
    assert dm_client.state.box.placed_bids.get_value(second_bidder.address) == [
        [
            [first_seller.address, asset_to_sell],
            cst.AMOUNT_TO_OUTBID.micro_algo,
        ]
    ]
    assert dm_client.state.local_state(
        second_bidder.address
    ).deposited - deposited_before_call == -(
        (cst.PLACED_BIDS_BOX_MBR + cst.AMOUNT_TO_OUTBID).micro_algo
    )


def test_fail_worse_bid(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_first_bidder_bid: Callable,
    first_seller: SigningAccount,
    second_bidder: SigningAccount,
) -> None:
    with pytest.raises(LogicError, match=err.WORSE_BID):
        dm_client.send.bid(
            BidArgs(
                sale_key=SaleKey(owner=first_seller.address, asset=asset_to_sell),
                new_bid_amount=cst.AMOUNT_TO_BID.micro_algo - 1,
            ),
            params=CommonAppCallParams(sender=second_bidder.address),
            send_params=SendParams(populate_app_call_resources=True),
        )


def test_fail_same_bid(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_first_bidder_bid: Callable,
    first_seller: SigningAccount,
    second_bidder: SigningAccount,
) -> None:
    with pytest.raises(LogicError, match=err.WORSE_BID):
        dm_client.send.bid(
            BidArgs(
                sale_key=SaleKey(owner=first_seller.address, asset=asset_to_sell),
                new_bid_amount=cst.AMOUNT_TO_BID.micro_algo,
            ),
            params=CommonAppCallParams(sender=second_bidder.address),
            send_params=SendParams(populate_app_call_resources=True),
        )


def test_pass_multiple_placed_bid(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
    second_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    first_sale_key = SaleKey(owner=first_seller.address, asset=asset_to_sell)
    second_sale_key = SaleKey(owner=second_seller.address, asset=asset_to_sell)
    assert dm_client.state.box.sales.get_value(first_sale_key).bid == []
    assert dm_client.state.box.sales.get_value(second_sale_key).bid == []

    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.placed_bids.get_value(first_bidder.address)

    deposited_before_call = dm_client.state.local_state(first_bidder.address).deposited

    dm_client.new_group().bid(
        BidArgs(
            sale_key=first_sale_key,
            new_bid_amount=cst.AMOUNT_TO_BID.micro_algo,
        ),
    ).bid(
        BidArgs(
            sale_key=second_sale_key,
            new_bid_amount=cst.AMOUNT_TO_BID.micro_algo,
        )
    ).send(
        send_params=SendParams(populate_app_call_resources=True)
    )

    assert dm_client.state.box.sales.get_value(first_sale_key).bid == [
        [first_bidder.address, cst.AMOUNT_TO_BID.micro_algo]
    ]
    assert dm_client.state.box.sales.get_value(second_sale_key).bid == [
        [first_bidder.address, cst.AMOUNT_TO_BID.micro_algo]
    ]
    assert dm_client.state.box.placed_bids.get_value(first_bidder.address) == [
        [[first_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo],
        [[second_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo],
    ]
    assert dm_client.state.local_state(
        first_bidder.address
    ).deposited - deposited_before_call == -(
        2 * cst.AMOUNT_TO_BID.micro_algo + cst.PLACED_BIDS_BOX_MBR.micro_algo
    )


def test_pass_repeatedly_placed_bid(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_first_bidder_bid: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    sale_key = SaleKey(owner=first_seller.address, asset=asset_to_sell)

    assert dm_client.state.box.sales.get_value(sale_key).bid == [
        [
            first_bidder.address,
            cst.AMOUNT_TO_BID.micro_algo,
        ]
    ]
    assert dm_client.state.box.placed_bids.get_value(first_bidder.address) == [
        [[first_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo]
    ]
    deposited_before_call = dm_client.state.local_state(first_bidder.address).deposited

    dm_client.send.bid(
        BidArgs(
            sale_key=SaleKey(owner=first_seller.address, asset=asset_to_sell),
            new_bid_amount=cst.AMOUNT_TO_BID.micro_algo + 1,
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )

    assert dm_client.state.box.sales.get_value(sale_key).bid == [
        [first_bidder.address, cst.AMOUNT_TO_BID.micro_algo + 1]
    ]
    assert dm_client.state.box.placed_bids.get_value(first_bidder.address) == [
        [[first_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo + 1],
    ]
    assert (
        dm_client.state.local_state(first_bidder.address).deposited
        - deposited_before_call
        == -1
    )


def test_pass_repeatedly_placed_bid_exact_deposited(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_first_bidder_bid: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    # TODO: Write docstrings for all tests
    # Here we want to up our bid by 1 microALGO and we want to have exactly 1 microALGO in the balance.
    # This test verifies that, when you are overwriting one of your own bids,
    #  you get your money back before giving the new bid amount again.
    # This way you only need to have the diff amount in your balance instead of the new amount.
    # We could (should) write a new test fixture for this but withdrawing from a
    #  known fixture results in the same outcome.
    dm_client.send.withdraw(
        WithdrawArgs(
            amount=(
                cst.AMOUNT_TO_DEPOSIT - cst.AMOUNT_TO_BID - cst.PLACED_BIDS_BOX_MBR
            ).micro_algo
            - 1
        ),
        params=CommonAppCallParams(extra_fee=AlgoAmount(micro_algo=1_000)),
    )

    sale_key = SaleKey(owner=first_seller.address, asset=asset_to_sell)

    assert dm_client.state.box.sales.get_value(sale_key).bid == [
        [
            first_bidder.address,
            cst.AMOUNT_TO_BID.micro_algo,
        ]
    ]
    assert dm_client.state.box.placed_bids.get_value(first_bidder.address) == [
        [[first_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo]
    ]
    assert (
        dm_client.state.local_state(first_bidder.address).deposited
        == AlgoAmount(micro_algo=1).micro_algo
    )

    dm_client.send.bid(
        BidArgs(
            sale_key=SaleKey(owner=first_seller.address, asset=asset_to_sell),
            new_bid_amount=cst.AMOUNT_TO_BID.micro_algo + 1,
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )

    assert dm_client.state.box.sales.get_value(sale_key).bid == [
        [first_bidder.address, cst.AMOUNT_TO_BID.micro_algo + 1]
    ]
    assert dm_client.state.box.placed_bids.get_value(first_bidder.address) == [
        [[first_seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo + 1],
    ]

    assert (
        dm_client.state.local_state(first_bidder.address).deposited
        == AlgoAmount(micro_algo=0).micro_algo
    )
