import consts as cst
import pytest
from algokit_utils import AlgoAmount, AlgorandClient, AssetCreateParams, SigningAccount

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    DigitalMarketplaceClient,
    DigitalMarketplaceFactory,
)


@pytest.fixture(scope="session")
def deployer(algorand_client: AlgorandClient) -> SigningAccount:
    account = algorand_client.account.from_environment("DEPLOYER")
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=AlgoAmount.from_algo(cst.AMOUNT_TO_FUND),
    )
    return account


@pytest.fixture(scope="session")
def seller(algorand_client: AlgorandClient) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=AlgoAmount.from_algo(cst.AMOUNT_TO_FUND),
    )
    return account


@pytest.fixture(scope="session")
def buyer(algorand_client: AlgorandClient) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=AlgoAmount.from_algo(cst.AMOUNT_TO_FUND),
    )
    return account


@pytest.fixture(scope="session")
def bidder(algorand_client: AlgorandClient) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=AlgoAmount.from_algo(cst.AMOUNT_TO_FUND),
    )
    return account


@pytest.fixture(scope="function")
def random_account(algorand_client: AlgorandClient) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=AlgoAmount.from_algo(cst.AMOUNT_TO_FUND),
    )
    return account


@pytest.fixture(scope="session")
def asset_to_sell(algorand_client: AlgorandClient, seller: SigningAccount) -> int:
    result = algorand_client.send.asset_create(
        AssetCreateParams(
            sender=seller.address,
            total=cst.ASA_AMOUNT_TO_CREATE,
            decimals=cst.ASA_DECIMALS,
        )
    )
    return result.asset_id


@pytest.fixture(scope="function")
def digital_marketplace_client(
    algorand_client: AlgorandClient, deployer: SigningAccount
) -> DigitalMarketplaceClient:
    factory = algorand_client.client.get_typed_app_factory(
        DigitalMarketplaceFactory, default_sender=deployer.address
    )

    client, _ = factory.send.create.bare()
    algorand_client.account.ensure_funded(
        client.app_address,
        dispenser_account=algorand_client.account.dispenser_from_environment(),
        min_spending_balance=AlgoAmount.from_algo(0),
    )
    return client


@pytest.fixture(scope="function")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient, random_account: SigningAccount
) -> DigitalMarketplaceClient:
    return digital_marketplace_client.clone(default_sender=random_account.address)
