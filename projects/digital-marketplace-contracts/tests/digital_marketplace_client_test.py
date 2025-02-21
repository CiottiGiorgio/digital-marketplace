import algokit_utils
import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    PaymentParams,
    SigningAccount,
)

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    DepositArgs,
    DigitalMarketplaceClient,
    DigitalMarketplaceFactory,
)

AMOUNT_TO_FUND = 10
AMOUNT_TO_DEPOSIT = 8
assert AMOUNT_TO_DEPOSIT > 1


@pytest.fixture(scope="session")
def deployer(algorand_client: AlgorandClient) -> SigningAccount:
    account = algorand_client.account.from_environment("DEPLOYER")
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=AlgoAmount.from_algo(AMOUNT_TO_FUND),
    )
    return account


@pytest.fixture(scope="session")
def seller(algorand_client: AlgorandClient) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=AlgoAmount.from_algo(AMOUNT_TO_FUND),
    )
    return account


@pytest.fixture(scope="session")
def buyer(algorand_client: AlgorandClient) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=AlgoAmount.from_algo(AMOUNT_TO_FUND),
    )
    return account


@pytest.fixture(scope="session")
def bidder(algorand_client: AlgorandClient) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=AlgoAmount.from_algo(AMOUNT_TO_FUND),
    )
    return account


@pytest.fixture(scope="session")
def digital_marketplace_client(
    algorand_client: AlgorandClient, deployer: SigningAccount
) -> DigitalMarketplaceClient:
    factory = algorand_client.client.get_typed_app_factory(
        DigitalMarketplaceFactory, default_sender=deployer.address
    )

    client, _ = factory.deploy(
        on_schema_break=algokit_utils.OnSchemaBreak.AppendApp,
        on_update=algokit_utils.OnUpdate.AppendApp,
    )
    return client


@pytest.mark.parametrize("actor", ["seller", "buyer", "bidder"])
def test_opt_in_deposit(
    digital_marketplace_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    actor: str,
    request: pytest.FixtureRequest,
) -> None:
    actor_fixture: SigningAccount = request.getfixturevalue(actor)

    dm_client = digital_marketplace_client.clone(default_sender=actor_fixture.address)
    result = dm_client.send.opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=actor_fixture.address,
                    signer=actor_fixture.signer,
                    receiver=dm_client.app_address,
                    amount=AlgoAmount.from_algo(1),
                )
            )
        )
    )
    assert result.confirmation

    assert (
        dm_client.state.local_state(actor_fixture.address).deposited
        == AlgoAmount.from_algo(1).micro_algo
    )


@pytest.mark.parametrize("actor", ["seller", "buyer", "bidder"])
def test_noop_deposit(
    digital_marketplace_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    actor: str,
    request: pytest.FixtureRequest,
) -> None:
    actor_fixture: SigningAccount = request.getfixturevalue(actor)

    dm_client = digital_marketplace_client.clone(default_sender=actor_fixture.address)
    result = dm_client.send.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=actor_fixture.address,
                    signer=actor_fixture.signer,
                    receiver=dm_client.app_address,
                    amount=AlgoAmount.from_algo(AMOUNT_TO_DEPOSIT - 1),
                )
            )
        )
    )
    assert result.confirmation

    assert (
        dm_client.state.local_state(actor_fixture.address).deposited
        == AlgoAmount.from_algo(AMOUNT_TO_DEPOSIT).micro_algo
    )
