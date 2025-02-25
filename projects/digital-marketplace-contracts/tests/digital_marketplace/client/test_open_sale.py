from typing import Callable

import consts as cst
import helpers
import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AssetOptInParams,
    AssetTransferParams,
    CommonAppCallParams,
    LogicError,
    PaymentParams,
    SendParams,
    SigningAccount,
)
from algosdk.atomic_transaction_composer import TransactionWithSigner

import smart_contracts.digital_marketplace.errors as err
from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    DepositArgs,
    DigitalMarketplaceClient,
    OpenSaleArgs,
    Sale,
    SaleKey,
    SponsorAssetArgs,
)


@pytest.fixture(scope="function")
def asset_holder(
    algorand_client: AlgorandClient, seller: SigningAccount, asset_to_sell: int
) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=AlgoAmount.from_algo(cst.AMOUNT_TO_FUND),
    )
    algorand_client.send.asset_opt_in(
        AssetOptInParams(sender=account.address, asset_id=asset_to_sell)
    )
    algorand_client.send.asset_transfer(
        AssetTransferParams(
            sender=seller.address,
            asset_id=asset_to_sell,
            amount=cst.ASA_AMOUNT_TO_SELL,
            receiver=account.address,
        )
    )
    return account


@pytest.fixture(scope="function")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient, seller: SigningAccount
) -> DigitalMarketplaceClient:
    return digital_marketplace_client.clone(default_sender=seller.address)


@pytest.fixture(scope="function")
def sponsor_asset_to_sell(
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    seller: SigningAccount,
    asset_to_sell: int,
) -> None:
    dm_client.new_group().opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=seller.address,
                    receiver=dm_client.app_address,
                    amount=AlgoAmount.from_algo(cst.AMOUNT_TO_DEPOSIT),
                )
            )
        )
    ).sponsor_asset(
        SponsorAssetArgs(asset=asset_to_sell),
        params=CommonAppCallParams(extra_fee=AlgoAmount.from_micro_algo(1_000)),
    ).send()


def test_fail_diff_sender_open_sale(
    dm_client: DigitalMarketplaceClient,
    sponsor_asset_to_sell: Callable,
    algorand_client: AlgorandClient,
    seller: SigningAccount,
    asset_holder: SigningAccount,
    asset_to_sell: int,
) -> None:
    with pytest.raises(LogicError, match=err.DIFFERENT_SENDER):
        dm_client.send.open_sale(
            OpenSaleArgs(
                asset_deposit=TransactionWithSigner(
                    txn=algorand_client.create_transaction.asset_transfer(
                        AssetTransferParams(
                            sender=asset_holder.address,
                            asset_id=asset_to_sell,
                            amount=cst.ASA_AMOUNT_TO_SELL,
                            receiver=dm_client.app_address,
                        )
                    ),
                    signer=asset_holder.signer,
                ),
                cost=AlgoAmount.from_algo(cst.COST_TO_BUY).micro_algo,
            )
        )


def test_fail_wrong_receiver_open_sale(
    dm_client: DigitalMarketplaceClient,
    sponsor_asset_to_sell: Callable,
    algorand_client: AlgorandClient,
    seller: SigningAccount,
    asset_holder: SigningAccount,
    asset_to_sell: int,
) -> None:
    with pytest.raises(LogicError, match=err.WRONG_RECEIVER):
        dm_client.send.open_sale(
            OpenSaleArgs(
                asset_deposit=TransactionWithSigner(
                    txn=algorand_client.create_transaction.asset_transfer(
                        AssetTransferParams(
                            sender=seller.address,
                            asset_id=asset_to_sell,
                            amount=cst.ASA_AMOUNT_TO_SELL,
                            receiver=asset_holder.address,
                        )
                    ),
                    signer=seller.signer,
                ),
                cost=AlgoAmount.from_algo(cst.COST_TO_BUY).micro_algo,
            )
        )


def test_fail_not_enough_deposited_open_sale(
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    seller: SigningAccount,
    asset_to_sell: int,
) -> None:
    dm_client.new_group().opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=seller.address,
                    receiver=dm_client.app_address,
                    # This is just enough to sponsor an asset but not enough to open a sales box.
                    amount=AlgoAmount.from_micro_algo(100_000),
                )
            )
        )
    ).sponsor_asset(
        SponsorAssetArgs(asset=asset_to_sell),
        params=CommonAppCallParams(extra_fee=AlgoAmount.from_micro_algo(1_000)),
    ).send()

    with pytest.raises(LogicError):
        dm_client.send.open_sale(
            OpenSaleArgs(
                asset_deposit=algorand_client.create_transaction.asset_transfer(
                    AssetTransferParams(
                        sender=seller.address,
                        asset_id=asset_to_sell,
                        amount=cst.ASA_AMOUNT_TO_SELL,
                        receiver=dm_client.app_address,
                    )
                ),
                cost=cst.COST_TO_BUY,
            ),
            send_params=SendParams(populate_app_call_resources=True),
        )


def test_pass_open_sale(
    dm_client: DigitalMarketplaceClient,
    sponsor_asset_to_sell: Callable,
    algorand_client: AlgorandClient,
    seller: SigningAccount,
    asset_to_sell: int,
) -> None:
    mbr_before_call = algorand_client.account.get_information(
        dm_client.app_address
    ).min_balance
    asa_balance_before_call = helpers.asa_amount(
        algorand_client,
        dm_client.app_address,
        asset_to_sell,
    )
    deposited_before_call = dm_client.state.local_state(seller.address).deposited

    dm_client.send.open_sale(
        OpenSaleArgs(
            asset_deposit=algorand_client.create_transaction.asset_transfer(
                AssetTransferParams(
                    sender=seller.address,
                    asset_id=asset_to_sell,
                    amount=cst.ASA_AMOUNT_TO_SELL,
                    receiver=dm_client.app_address,
                )
            ),
            cost=AlgoAmount.from_algo(cst.COST_TO_BUY).micro_algo,
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )

    asa_balance = helpers.asa_amount(
        algorand_client,
        dm_client.app_address,
        asset_to_sell,
    )

    # The created box does not contain a bid yet.
    # The mbr does not raise as much as the subtracted amount from the deposit.
    assert algorand_client.account.get_information(
        dm_client.app_address
    ).min_balance.micro_algo - mbr_before_call.micro_algo == 2_500 + 400 * (
        5 + 32 + 8 + 2 + 8 + 8 + 2
    )
    assert asa_balance - asa_balance_before_call == cst.ASA_AMOUNT_TO_SELL
    assert dm_client.state.local_state(
        seller.address
    ).deposited - deposited_before_call == -(
        2_500 + 400 * (5 + 32 + 8 + 2 + 8 + 8 + 2 + 32 + 8)
    )

    assert dm_client.state.box.sales.get_value(
        SaleKey(owner=seller.address, asset=asset_to_sell)
    ) == Sale(
        cst.ASA_AMOUNT_TO_SELL, AlgoAmount.from_algo(cst.COST_TO_BUY).micro_algo, []
    )
