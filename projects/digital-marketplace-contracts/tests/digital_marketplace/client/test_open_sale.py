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


@pytest.fixture(scope="module")
def asset_holder(
    algorand_client: AlgorandClient, first_seller: SigningAccount, asset_to_sell: int
) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=cst.AMOUNT_TO_FUND,
    )
    algorand_client.send.asset_opt_in(
        AssetOptInParams(sender=account.address, asset_id=asset_to_sell)
    )
    algorand_client.send.asset_transfer(
        AssetTransferParams(
            sender=first_seller.address,
            asset_id=asset_to_sell,
            amount=cst.ASA_AMOUNT_TO_SELL,
            receiver=account.address,
        )
    )
    return account


@pytest.fixture(scope="function")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient, first_seller: SigningAccount
) -> DigitalMarketplaceClient:
    return digital_marketplace_client.clone(default_sender=first_seller.address)


def test_fail_diff_sender_open_sale(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_sponsor_asset: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
    asset_holder: SigningAccount,
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
                cost=cst.COST_TO_BUY.micro_algo,
            )
        )


def test_fail_wrong_receiver_open_sale(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_sponsor_asset: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
    asset_holder: SigningAccount,
) -> None:
    with pytest.raises(LogicError, match=err.WRONG_RECEIVER):
        dm_client.send.open_sale(
            OpenSaleArgs(
                asset_deposit=TransactionWithSigner(
                    txn=algorand_client.create_transaction.asset_transfer(
                        AssetTransferParams(
                            sender=first_seller.address,
                            asset_id=asset_to_sell,
                            amount=cst.ASA_AMOUNT_TO_SELL,
                            receiver=asset_holder.address,
                        )
                    ),
                    signer=first_seller.signer,
                ),
                cost=cst.COST_TO_BUY.micro_algo,
            )
        )


def test_fail_not_enough_deposited_open_sale(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
) -> None:
    dm_client.new_group().opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=first_seller.address,
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
                        sender=first_seller.address,
                        asset_id=asset_to_sell,
                        amount=cst.ASA_AMOUNT_TO_SELL,
                        receiver=dm_client.app_address,
                    )
                ),
                cost=cst.COST_TO_BUY.micro_algo,
            ),
            send_params=SendParams(populate_app_call_resources=True),
        )


def test_fail_sale_already_exists_open_sale(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
    asset_holder: SigningAccount,
) -> None:
    with pytest.raises(LogicError, match=err.SALE_ALREADY_EXISTS):
        dm_client.send.open_sale(
            OpenSaleArgs(
                asset_deposit=algorand_client.create_transaction.asset_transfer(
                    AssetTransferParams(
                        sender=first_seller.address,
                        asset_id=asset_to_sell,
                        amount=cst.ASA_AMOUNT_TO_SELL,
                        receiver=dm_client.app_address,
                    )
                ),
                cost=cst.COST_TO_BUY.micro_algo,
            ),
            params=CommonAppCallParams(sender=first_seller.address),
            send_params=SendParams(populate_app_call_resources=True),
        )


def test_pass_open_sale(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_sponsor_asset: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
) -> None:
    mbr_before_call = algorand_client.account.get_information(
        dm_client.app_address
    ).min_balance
    asa_balance_before_call = helpers.asa_amount(
        algorand_client,
        dm_client.app_address,
        asset_to_sell,
    )
    deposited_before_call = dm_client.state.local_state(first_seller.address).deposited

    dm_client.send.open_sale(
        OpenSaleArgs(
            asset_deposit=algorand_client.create_transaction.asset_transfer(
                AssetTransferParams(
                    sender=first_seller.address,
                    asset_id=asset_to_sell,
                    amount=cst.ASA_AMOUNT_TO_SELL,
                    receiver=dm_client.app_address,
                )
            ),
            cost=cst.COST_TO_BUY.micro_algo,
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
    assert (
        algorand_client.account.get_information(dm_client.app_address).min_balance
        - mbr_before_call
        == cst.SALES_BOX_BASE_MBR
    )
    assert asa_balance - asa_balance_before_call == cst.ASA_AMOUNT_TO_SELL
    assert (
        dm_client.state.local_state(first_seller.address).deposited
        - deposited_before_call
        == -cst.SALES_BOX_MBR.micro_algo
    )

    assert dm_client.state.box.sales.get_value(
        SaleKey(owner=first_seller.address, asset=asset_to_sell)
    ) == Sale(cst.ASA_AMOUNT_TO_SELL, cst.COST_TO_BUY.micro_algo, [])
