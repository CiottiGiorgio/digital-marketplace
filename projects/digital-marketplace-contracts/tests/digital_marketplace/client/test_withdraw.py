from typing import Callable

import consts as cst
import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    LogicError,
    PaymentParams,
    SendParams,
    SigningAccount,
)

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
    dm_client.send.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=random_account.address,
                    receiver=dm_client.app_address,
                    amount=cst.DEPOSITED_BOX_MBR,
                )
            )
        ),
        params=CommonAppCallParams(sender=random_account.address),
        send_params=SendParams(populate_app_call_resources=True),
    )

    with pytest.raises(LogicError, match="- would result negative"):
        dm_client.send.withdraw(
            WithdrawArgs(amount=AlgoAmount(algo=1).micro_algo),
            params=CommonAppCallParams(
                extra_fee=AlgoAmount(micro_algo=1_000),
                sender=random_account.address,
            ),
            send_params=SendParams(populate_app_call_resources=True),
        )


def test_pass_partial_withdraw(
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
    deposited_before_call = dm_client.state.box.deposited.get_value(
        first_seller.address
    )

    dm_client.send.withdraw(
        WithdrawArgs(amount=cst.RESIDUAL_INITIAL_DEPOSIT.micro_algo - 1),
        params=CommonAppCallParams(extra_fee=AlgoAmount(micro_algo=1_000)),
        send_params=SendParams(populate_app_call_resources=True),
    )

    assert (
        algorand_client.account.get_information(first_seller.address).amount
        - balance_before_call
        == cst.RESIDUAL_INITIAL_DEPOSIT.micro_algo
        - 1
        - AlgoAmount(micro_algo=2_000).micro_algo
    )
    assert dm_client.state.box.deposited.get_value(
        first_seller.address
    ) - deposited_before_call == -(cst.RESIDUAL_INITIAL_DEPOSIT.micro_algo - 1)


def test_pass_full_withdraw(
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
        WithdrawArgs(amount=cst.RESIDUAL_INITIAL_DEPOSIT.micro_algo),
        params=CommonAppCallParams(extra_fee=AlgoAmount(micro_algo=1_000)),
        send_params=SendParams(populate_app_call_resources=True),
    )

    assert (
        algorand_client.account.get_information(first_seller.address).amount
        - balance_before_call
        == cst.RESIDUAL_INITIAL_DEPOSIT.micro_algo
        - AlgoAmount(micro_algo=2_000).micro_algo
    )
    assert dm_client.state.box.deposited.get_value(first_seller.address) == 0
