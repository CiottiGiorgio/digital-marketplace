from typing import Callable

import consts as cst
import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    LogicError,
    PaymentParams,
    SigningAccount,
)
from algosdk.error import AlgodHTTPError

import smart_contracts.digital_marketplace.errors as err
from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    DepositArgs,
    DigitalMarketplaceClient,
    WithdrawArgs,
)


@pytest.fixture(scope="function")
def deposit_into_dm(
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    random_account: SigningAccount,
) -> None:
    dm_client.send.opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=random_account.address,
                    receiver=dm_client.app_address,
                    amount=AlgoAmount.from_algo(cst.AMOUNT_TO_DEPOSIT),
                )
            )
        )
    )


def test_fail_overdraft_withdraw(
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    random_account: SigningAccount,
    asset_to_sell: int,
) -> None:
    dm_client.send.opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=random_account.address,
                    receiver=dm_client.app_address,
                    amount=AlgoAmount.from_algo(0),
                )
            )
        )
    )

    # FIXME: We need to catch a more granular error here.
    with pytest.raises(LogicError):
        dm_client.send.withdraw(WithdrawArgs(amount=AlgoAmount.from_algo(1).micro_algo))


def test_fail_close_out_with_balance_withdraw(
    dm_client: DigitalMarketplaceClient,
    deposit_into_dm: Callable,
    algorand_client: AlgorandClient,
    random_account: SigningAccount,
    asset_to_sell: int,
) -> None:
    with pytest.raises(LogicError, match=err.BALANCE_NOT_EMPTY):
        dm_client.send.close_out.withdraw(
            WithdrawArgs(
                amount=AlgoAmount.from_algo(cst.AMOUNT_TO_DEPOSIT).micro_algo - 1
            ),
            params=CommonAppCallParams(extra_fee=AlgoAmount.from_micro_algo(1_000)),
        )


def test_pass_noop_withdraw(
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    deposit_into_dm: Callable,
    random_account: SigningAccount,
) -> None:
    balance_before_call = algorand_client.account.get_information(
        random_account.address
    ).amount
    deposited_before_call = dm_client.state.local_state(
        random_account.address
    ).deposited

    dm_client.send.withdraw(
        WithdrawArgs(
            amount=AlgoAmount.from_algo(cst.AMOUNT_TO_DEPOSIT).micro_algo
        ),
        params=CommonAppCallParams(extra_fee=AlgoAmount.from_micro_algo(1_000)),
    )

    assert (
        algorand_client.account.get_information(random_account.address).amount
        - balance_before_call
        == AlgoAmount.from_algo(cst.AMOUNT_TO_DEPOSIT).micro_algo
        - AlgoAmount.from_micro_algo(2_000).micro_algo
    )
    assert (
        dm_client.state.local_state(random_account.address).deposited
        - deposited_before_call
        == -AlgoAmount.from_algo(cst.AMOUNT_TO_DEPOSIT).micro_algo
    )


def test_pass_close_out_withdraw(
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    deposit_into_dm: Callable,
    random_account: SigningAccount,
) -> None:
    balance_before_call = algorand_client.account.get_information(
        random_account.address
    ).amount

    dm_client.send.close_out.withdraw(
        WithdrawArgs(
            amount=AlgoAmount.from_algo(cst.AMOUNT_TO_DEPOSIT).micro_algo
        ),
        params=CommonAppCallParams(extra_fee=AlgoAmount.from_micro_algo(1_000)),
    )

    assert (
        algorand_client.account.get_information(random_account.address).amount
        - balance_before_call
        == AlgoAmount.from_algo(cst.AMOUNT_TO_DEPOSIT).micro_algo
        - AlgoAmount.from_micro_algo(2_000).micro_algo
    )
    with pytest.raises(AlgodHTTPError, match="account application info not found"):
        _ = dm_client.state.local_state(random_account.address).deposited
