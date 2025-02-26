from typing import Callable

import consts as cst
import pytest
from algokit_utils import (
    SendParams,
    AlgorandClient,
    SigningAccount,
    PaymentParams,
)
from algosdk.error import AlgodHTTPError

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    BidArgs,
    DigitalMarketplaceClient,
    SaleKey,
    DepositArgs,
)


@pytest.fixture(scope="function")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient, bidder: SigningAccount
) -> DigitalMarketplaceClient:
    return digital_marketplace_client.clone(default_sender=bidder.address)


def test_pass_first_placed_bid_first_bid(
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    seller: SigningAccount,
    bidder: SigningAccount,
    asset_to_sell: int,
) -> None:
    assert (
        dm_client.state.box.sales.get_value(
            SaleKey(owner=seller.address, asset=asset_to_sell)
        ).bid
        == []
    )
    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.placed_bids.get_value(bidder.address)
    deposited_before_call = dm_client.state.local_state(bidder.address).deposited

    dm_client.send.bid(
        BidArgs(
            sale_key=SaleKey(owner=seller.address, asset=asset_to_sell),
            new_bid_amount=cst.AMOUNT_TO_BID.micro_algo,
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )

    assert dm_client.state.box.sales.get_value(
        SaleKey(owner=seller.address, asset=asset_to_sell)
    ).bid == [[bidder.address, cst.AMOUNT_TO_BID.micro_algo]]
    assert dm_client.state.box.placed_bids.get_value(bidder.address) == [
        [
            [seller.address, asset_to_sell],
            cst.AMOUNT_TO_BID.micro_algo,
        ]
    ]
    assert (
        dm_client.state.local_state(bidder.address).deposited - deposited_before_call
        == -(cst.PLACED_BIDS_BOX_MBR + cst.AMOUNT_TO_BID).micro_algo
    )


def test_pass_first_placed_bid_second_bid(
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    algorand_client: AlgorandClient,
    seller: SigningAccount,
    bidder: SigningAccount,
    random_account: SigningAccount,
    asset_to_sell: int,
) -> None:
    dm_client.clone(default_sender=random_account.address).new_group().opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=random_account.address,
                    receiver=dm_client.app_address,
                    amount=cst.AMOUNT_TO_DEPOSIT,
                )
            )
        )
    ).bid(
        BidArgs(
            sale_key=SaleKey(owner=seller.address, asset=asset_to_sell),
            new_bid_amount=cst.AMOUNT_TO_BID.micro_algo - 1,
        )
    ).send(send_params=SendParams(populate_app_call_resources=True))

    assert (
        dm_client.state.box.sales.get_value(
            SaleKey(owner=seller.address, asset=asset_to_sell)
        ).bid
        == [[random_account.address, cst.AMOUNT_TO_BID.micro_algo - 1]]
    )
    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.placed_bids.get_value(bidder.address)
    deposited_before_call = dm_client.state.local_state(bidder.address).deposited

    dm_client.send.bid(
        BidArgs(
            sale_key=SaleKey(owner=seller.address, asset=asset_to_sell),
            new_bid_amount=cst.AMOUNT_TO_BID.micro_algo,
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )

    assert dm_client.state.box.sales.get_value(
        SaleKey(owner=seller.address, asset=asset_to_sell)
    ).bid == [[bidder.address, cst.AMOUNT_TO_BID.micro_algo]]
    assert dm_client.state.box.placed_bids.get_value(bidder.address) == [
        [
            [seller.address, asset_to_sell],
            cst.AMOUNT_TO_BID.micro_algo,
        ]
    ]
    assert (
        dm_client.state.local_state(bidder.address).deposited - deposited_before_call
        == -(cst.PLACED_BIDS_BOX_MBR + cst.AMOUNT_TO_BID).micro_algo
    )
