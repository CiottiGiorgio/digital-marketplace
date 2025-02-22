import algokit_utils
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


@pytest.fixture(scope="module")
def seller(algorand_client: AlgorandClient) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=AlgoAmount.from_algo(cst.AMOUNT_TO_FUND),
    )
    return account


@pytest.fixture(scope="module")
def buyer(algorand_client: AlgorandClient) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=AlgoAmount.from_algo(cst.AMOUNT_TO_FUND),
    )
    return account


@pytest.fixture(scope="module")
def bidder(algorand_client: AlgorandClient) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=AlgoAmount.from_algo(cst.AMOUNT_TO_FUND),
    )
    return account


@pytest.fixture(scope="module")
def asset_to_sell(algorand_client: AlgorandClient, seller: SigningAccount) -> int:
    result = algorand_client.send.asset_create(
        AssetCreateParams(
            sender=seller.address,
            total=cst.ASA_AMOUNT_TO_CREATE,
            decimals=cst.ASA_DECIMALS,
        )
    )
    return result.asset_id


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
