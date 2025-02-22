import consts as cst
import pytest
from algokit_utils import AlgoAmount, AlgorandClient, PaymentParams, SigningAccount

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    DepositArgs,
    DigitalMarketplaceClient,
)


@pytest.fixture(scope="module")
def generic_actor(algorand_client: AlgorandClient) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=AlgoAmount.from_algo(cst.AMOUNT_TO_FUND),
    )
    return account


@pytest.fixture(scope="module")
def dm_client(digital_marketplace_client: DigitalMarketplaceClient, generic_actor: SigningAccount) -> DigitalMarketplaceClient:
    return digital_marketplace_client.clone(default_sender=generic_actor.address)


def test_opt_in_deposit(
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    generic_actor: SigningAccount
) -> None:
    result = dm_client.send.opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=generic_actor.address,
                    signer=generic_actor.signer,
                    receiver=dm_client.app_address,
                    amount=AlgoAmount.from_algo(1),
                )
            )
        )
    )
    assert result.confirmation

    assert (
        dm_client.state.local_state(generic_actor.address).deposited
        == AlgoAmount.from_algo(1).micro_algo
    )


def test_noop_deposit(
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    generic_actor: SigningAccount
) -> None:
    result = dm_client.send.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=generic_actor.address,
                    receiver=dm_client.app_address,
                    amount=AlgoAmount.from_algo(cst.AMOUNT_TO_DEPOSIT - 1),
                )
            )
        )
    )
    assert result.confirmation

    assert (
        dm_client.state.local_state(generic_actor.address).deposited
        == AlgoAmount.from_algo(cst.AMOUNT_TO_DEPOSIT).micro_algo
    )
