import algokit_utils
import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AssetCreateParams,
    AssetTransferParams,
    CommonAppCallParams,
    PaymentParams,
    SendParams,
    SigningAccount,
)

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    DepositArgs,
    DigitalMarketplaceClient,
    DigitalMarketplaceFactory,
    OpenSaleArgs,
    Sale,
    SaleKey,
    SponsorAssetArgs,
)

AMOUNT_TO_FUND = 10
AMOUNT_TO_DEPOSIT = 8
assert AMOUNT_TO_DEPOSIT > 1

AMOUNT_TO_SELL = 2_000
COST_TO_BUY = 5


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
def asset_to_sell(algorand_client: AlgorandClient, seller: SigningAccount) -> int:
    result = algorand_client.send.asset_create(
        AssetCreateParams(sender=seller.address, total=100_000, decimals=3)
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


def test_sponsor_asset(
    digital_marketplace_client: DigitalMarketplaceClient,
    seller: SigningAccount,
    asset_to_sell: int,
) -> None:
    dm_client = digital_marketplace_client.clone(default_sender=seller.address)

    balance_before_call = dm_client.state.local_state(seller.address).deposited

    dm_client.send.sponsor_asset(
        SponsorAssetArgs(asset=asset_to_sell),
        params=CommonAppCallParams(extra_fee=AlgoAmount.from_micro_algo(1_000)),
    )

    assert (
        dm_client.state.local_state(seller.address).deposited - balance_before_call
        == -AlgoAmount.from_micro_algo(100_000).micro_algo
    )


def test_open_sale(
    digital_marketplace_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    seller: SigningAccount,
    asset_to_sell: int,
) -> None:
    dm_client = digital_marketplace_client.clone(default_sender=seller.address)

    dm_client.send.open_sale(
        OpenSaleArgs(
            asset_deposit=algorand_client.create_transaction.asset_transfer(
                AssetTransferParams(
                    sender=seller.address,
                    asset_id=asset_to_sell,
                    receiver=dm_client.app_address,
                    amount=AMOUNT_TO_SELL,
                )
            ),
            cost=AlgoAmount.from_algo(COST_TO_BUY).micro_algo,
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )

    assert dm_client.state.box.sales.get_value(
        SaleKey(owner=seller.address, asset=asset_to_sell)
    ) == Sale(AlgoAmount.from_algo(COST_TO_BUY).micro_algo, [])
