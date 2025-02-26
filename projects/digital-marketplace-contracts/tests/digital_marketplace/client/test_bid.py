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


@pytest.fixture(scope="function")
def scenario_random_account_bid(
    digital_marketplace_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    seller: SigningAccount,
    random_account: SigningAccount,
    asset_to_sell: int,
) -> None:
    digital_marketplace_client.clone(
        default_sender=random_account.address
    ).new_group().opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=random_account.address,
                    receiver=digital_marketplace_client.app_address,
                    amount=cst.AMOUNT_TO_DEPOSIT,
                )
            )
        )
    ).bid(
        BidArgs(
            sale_key=SaleKey(owner=seller.address, asset=asset_to_sell),
            new_bid_amount=cst.AMOUNT_TO_BID.micro_algo,
        )
    ).send(
        send_params=SendParams(populate_app_call_resources=True)
    )


@pytest.fixture(scope="function")
def scenario_random_account_open_sale(
    digital_marketplace_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    seller: SigningAccount,
    random_account: SigningAccount,
    asset_to_sell: int,
) -> None:
    digital_marketplace_client.clone(
        default_sender=random_account.address
    ).new_group().add_transaction(
        algorand_client.create_transaction.asset_opt_in(
            AssetOptInParams(sender=random_account.address, asset_id=asset_to_sell)
        )
    ).add_transaction(
        txn=algorand_client.create_transaction.asset_transfer(
            AssetTransferParams(
                sender=seller.address,
                asset_id=asset_to_sell,
                amount=cst.ASA_AMOUNT_TO_SELL,
                receiver=random_account.address,
            )
        ),
        signer=seller.signer,
    ).opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=random_account.address,
                    receiver=digital_marketplace_client.app_address,
                    amount=cst.AMOUNT_TO_DEPOSIT,
                )
            )
        )
    ).open_sale(
        OpenSaleArgs(
            asset_deposit=algorand_client.create_transaction.asset_transfer(
                AssetTransferParams(
                    sender=random_account.address,
                    asset_id=asset_to_sell,
                    amount=cst.ASA_AMOUNT_TO_SELL,
                    receiver=digital_marketplace_client.app_address,
                )
            ),
            cost=cst.COST_TO_BUY.micro_algo,
        )
    ).send(
        send_params=SendParams(populate_app_call_resources=True)
    )


def test_pass_first_placed_bid_first_bid(
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    seller: SigningAccount,
    first_bidder: SigningAccount,
    asset_to_sell: int,
) -> None:
    sale_key = SaleKey(owner=seller.address, asset=asset_to_sell)
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
            [seller.address, asset_to_sell],
            cst.AMOUNT_TO_BID.micro_algo,
        ]
    ]
    assert (
        dm_client.state.local_state(first_bidder.address).deposited
        - deposited_before_call
        == -(cst.PLACED_BIDS_BOX_MBR + cst.AMOUNT_TO_BID).micro_algo
    )


def test_pass_first_placed_bid_better_bid(
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    algorand_client: AlgorandClient,
    seller: SigningAccount,
    first_bidder: SigningAccount,
    random_account: SigningAccount,
    scenario_random_account_bid: Callable,
    asset_to_sell: int,
) -> None:
    sale_key = SaleKey(owner=seller.address, asset=asset_to_sell)
    assert dm_client.state.box.sales.get_value(sale_key).bid == [
        [random_account.address, cst.AMOUNT_TO_BID.micro_algo]
    ]
    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.placed_bids.get_value(first_bidder.address)
    deposited_before_call = dm_client.state.local_state(first_bidder.address).deposited

    dm_client.send.bid(
        BidArgs(
            sale_key=sale_key,
            new_bid_amount=cst.AMOUNT_TO_BID.micro_algo + 1,
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )

    assert dm_client.state.box.sales.get_value(sale_key).bid == [
        [first_bidder.address, cst.AMOUNT_TO_BID.micro_algo + 1]
    ]
    assert dm_client.state.box.placed_bids.get_value(first_bidder.address) == [
        [
            [seller.address, asset_to_sell],
            cst.AMOUNT_TO_BID.micro_algo + 1,
        ]
    ]
    assert dm_client.state.local_state(
        first_bidder.address
    ).deposited - deposited_before_call == -(
        (cst.PLACED_BIDS_BOX_MBR + cst.AMOUNT_TO_BID).micro_algo + 1
    )


def test_fail_worse_bid(
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    scenario_random_account_bid: Callable,
    seller: SigningAccount,
    asset_to_sell: int,
) -> None:
    with pytest.raises(LogicError, match=err.WORSE_BID):
        dm_client.send.bid(
            BidArgs(
                sale_key=SaleKey(owner=seller.address, asset=asset_to_sell),
                new_bid_amount=cst.AMOUNT_TO_BID.micro_algo - 1,
            ),
            send_params=SendParams(populate_app_call_resources=True),
        )


def test_fail_same_bid(
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    scenario_random_account_bid: Callable,
    seller: SigningAccount,
    asset_to_sell: int,
) -> None:
    with pytest.raises(LogicError, match=err.WORSE_BID):
        dm_client.send.bid(
            BidArgs(
                sale_key=SaleKey(owner=seller.address, asset=asset_to_sell),
                new_bid_amount=cst.AMOUNT_TO_BID.micro_algo,
            ),
            send_params=SendParams(populate_app_call_resources=True),
        )


def test_pass_multiple_placed_bid(
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    scenario_random_account_open_sale: Callable,
    algorand_client: AlgorandClient,
    seller: SigningAccount,
    first_bidder: SigningAccount,
    random_account: SigningAccount,
    asset_to_sell: int,
) -> None:
    seller_sale_key = SaleKey(owner=seller.address, asset=asset_to_sell)
    random_account_sale_key = SaleKey(owner=random_account.address, asset=asset_to_sell)
    assert dm_client.state.box.sales.get_value(seller_sale_key).bid == []
    assert dm_client.state.box.sales.get_value(random_account_sale_key).bid == []

    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.placed_bids.get_value(first_bidder.address)

    deposited_before_call = dm_client.state.local_state(first_bidder.address).deposited

    dm_client.new_group().bid(
        BidArgs(
            sale_key=SaleKey(owner=seller.address, asset=asset_to_sell),
            new_bid_amount=cst.AMOUNT_TO_BID.micro_algo,
        ),
    ).bid(
        BidArgs(
            sale_key=SaleKey(owner=random_account.address, asset=asset_to_sell),
            new_bid_amount=cst.AMOUNT_TO_BID.micro_algo,
        )
    ).send(
        send_params=SendParams(populate_app_call_resources=True)
    )

    assert dm_client.state.box.sales.get_value(seller_sale_key).bid == [
        [first_bidder.address, cst.AMOUNT_TO_BID.micro_algo]
    ]
    assert dm_client.state.box.sales.get_value(random_account_sale_key).bid == [
        [first_bidder.address, cst.AMOUNT_TO_BID.micro_algo]
    ]
    assert dm_client.state.box.placed_bids.get_value(first_bidder.address) == [
        [[seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo],
        [[random_account.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo],
    ]
    assert dm_client.state.local_state(
        first_bidder.address
    ).deposited - deposited_before_call == -(
        2 * cst.AMOUNT_TO_BID.micro_algo + cst.PLACED_BIDS_BOX_MBR.micro_algo
    )


def test_pass_repeatedly_placed_bid(
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    algorand_client: AlgorandClient,
    seller: SigningAccount,
    first_bidder: SigningAccount,
    asset_to_sell: int,
) -> None:
    sale_key = SaleKey(owner=seller.address, asset=asset_to_sell)

    dm_client.send.bid(
        BidArgs(
            sale_key=SaleKey(owner=seller.address, asset=asset_to_sell),
            new_bid_amount=cst.AMOUNT_TO_BID.micro_algo,
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )

    assert dm_client.state.box.sales.get_value(sale_key).bid == [
        [
            first_bidder.address,
            cst.AMOUNT_TO_BID.micro_algo,
        ]
    ]
    assert dm_client.state.box.placed_bids.get_value(first_bidder.address) == [
        [[seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo]
    ]
    deposited_before_call = dm_client.state.local_state(first_bidder.address).deposited

    dm_client.send.bid(
        BidArgs(
            sale_key=SaleKey(owner=seller.address, asset=asset_to_sell),
            new_bid_amount=cst.AMOUNT_TO_BID.micro_algo + 1,
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )

    assert dm_client.state.box.sales.get_value(sale_key).bid == [
        [first_bidder.address, cst.AMOUNT_TO_BID.micro_algo + 1]
    ]
    assert dm_client.state.box.placed_bids.get_value(first_bidder.address) == [
        [[seller.address, asset_to_sell], cst.AMOUNT_TO_BID.micro_algo + 1],
    ]
    assert (
        dm_client.state.local_state(first_bidder.address).deposited
        - deposited_before_call
        == -1
    )
