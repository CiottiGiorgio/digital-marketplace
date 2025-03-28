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

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    DepositArgs,
    DigitalMarketplaceClient,
    WithdrawArgs,
)


def test_fail_overdraft_withdraw(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    random_account: SigningAccount,
) -> None:
    """
    Test that a withdrawal fails if the amount to withdraw exceeds the deposited amount.
    """
    dm_client.send.opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=random_account.address,
                    receiver=dm_client.app_address,
                    amount=AlgoAmount(algo=0),
                )
            )
        ),
        params=CommonAppCallParams(sender=random_account.address),
    )

    with pytest.raises(LogicError, match="- would result negative"):
        dm_client.send.withdraw(
            WithdrawArgs(amount=AlgoAmount(algo=1).micro_algo),
            params=CommonAppCallParams(
                extra_fee=AlgoAmount(micro_algo=1_000),
                sender=random_account.address,
            ),
        )


def test_pass_noop_partial_withdraw(
    dm_client: DigitalMarketplaceClient,
    scenario_deposit: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
) -> None:
    """
    Test that a partial withdrawal succeeds and updates the deposited field correctly.
    """
    balance_before_call = algorand_client.account.get_information(
        first_seller.address
    ).amount
    deposited_before_call = dm_client.state.local_state(first_seller.address).deposited

    dm_client.send.withdraw(
        WithdrawArgs(amount=cst.AMOUNT_TO_DEPOSIT.micro_algo - 1),
        params=CommonAppCallParams(extra_fee=AlgoAmount(micro_algo=1_000)),
    )

    assert (
        algorand_client.account.get_information(first_seller.address).amount
        - balance_before_call
        == cst.AMOUNT_TO_DEPOSIT.micro_algo
        - 1
        - AlgoAmount(micro_algo=2_000).micro_algo
    )
    assert dm_client.state.local_state(
        first_seller.address
    ).deposited - deposited_before_call == -(cst.AMOUNT_TO_DEPOSIT.micro_algo - 1)


def test_pass_noop_full_withdraw(
    dm_client: DigitalMarketplaceClient,
    scenario_deposit: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
) -> None:
    """
    Test that a full withdrawal succeeds and updates the local state correctly.
    """
    balance_before_call = algorand_client.account.get_information(
        first_seller.address
    ).amount

    dm_client.send.withdraw(
        WithdrawArgs(amount=cst.AMOUNT_TO_DEPOSIT.micro_algo),
        params=CommonAppCallParams(extra_fee=AlgoAmount(micro_algo=1_000)),
    )

    assert (
        algorand_client.account.get_information(first_seller.address).amount
        - balance_before_call
        == cst.AMOUNT_TO_DEPOSIT.micro_algo - AlgoAmount(micro_algo=2_000).micro_algo
    )
    assert dm_client.state.local_state(first_seller.address).deposited == 0


def test_pass_close_out_withdraw(
    dm_client: DigitalMarketplaceClient,
    scenario_deposit: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
) -> None:
    """
    Test that a close-out withdraw succeeds and removes the local state.
    """
    balance_before_call = algorand_client.account.get_information(
        first_seller.address
    ).amount

    # When called with CloseOut, the withdraw method will send back all
    #  available balance regardless of amount argument.
    dm_client.send.close_out.withdraw(
        WithdrawArgs(amount=0),
        params=CommonAppCallParams(extra_fee=AlgoAmount(micro_algo=1_000)),
    )

    assert (
        algorand_client.account.get_information(first_seller.address).amount
        - balance_before_call
        == cst.AMOUNT_TO_DEPOSIT.micro_algo - AlgoAmount(micro_algo=2_000).micro_algo
    )
    with pytest.raises(AlgodHTTPError, match="account application info not found"):
        _ = dm_client.state.local_state(first_seller.address).deposited
