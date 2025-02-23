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

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    DepositArgs,
    DigitalMarketplaceClient,
    WithdrawArgs,
)


@pytest.fixture(scope="function")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient, random_account: SigningAccount
) -> DigitalMarketplaceClient:
    return digital_marketplace_client.clone(default_sender=random_account.address)


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


def test_pass_withdraw(
    dm_client: DigitalMarketplaceClient,
    deposit_into_dm: Callable,
    random_account: SigningAccount,
) -> None:
    result = dm_client.send.withdraw(
        WithdrawArgs(amount=cst.AMOUNT_TO_DEPOSIT),
        params=CommonAppCallParams(extra_fee=AlgoAmount.from_micro_algo(1_000)),
    )

    assert result.confirmation
