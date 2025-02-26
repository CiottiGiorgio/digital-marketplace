from typing import Callable

import consts as cst
import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AssetCreateParams,
    AssetOptInParams,
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
    SponsorAssetArgs,
)


@pytest.fixture(scope="session")
def deployer(algorand_client: AlgorandClient) -> SigningAccount:
    account = algorand_client.account.from_environment("DEPLOYER")
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=cst.AMOUNT_TO_FUND,
    )
    return account


@pytest.fixture(scope="session")
def seller(algorand_client: AlgorandClient) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=cst.AMOUNT_TO_FUND,
    )
    return account


@pytest.fixture(scope="session")
def buyer(algorand_client: AlgorandClient) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=cst.AMOUNT_TO_FUND,
    )
    return account


@pytest.fixture(scope="session")
def bidder(algorand_client: AlgorandClient) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=cst.AMOUNT_TO_FUND,
    )
    return account


@pytest.fixture(scope="function")
def random_account(algorand_client: AlgorandClient) -> SigningAccount:
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=cst.AMOUNT_TO_FUND,
    )
    return account


@pytest.fixture(scope="session")
def asset_to_sell(
    algorand_client: AlgorandClient,
    seller: SigningAccount,
    buyer: SigningAccount,
    bidder: SigningAccount,
) -> int:
    result = algorand_client.send.asset_create(
        AssetCreateParams(
            sender=seller.address,
            total=cst.ASA_AMOUNT_TO_CREATE,
            decimals=cst.ASA_DECIMALS,
        )
    )
    algorand_client.new_group().add_asset_opt_in(
        AssetOptInParams(sender=buyer.address, asset_id=result.asset_id)
    ).add_asset_opt_in(
        AssetOptInParams(sender=bidder.address, asset_id=result.asset_id)
    ).send()

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
def scenario_deposit(
    digital_marketplace_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    seller: SigningAccount,
    buyer: SigningAccount,
    bidder: SigningAccount,
) -> None:
    deposit_group = digital_marketplace_client.new_group()
    for account in [seller, buyer]:
        deposit_group = deposit_group.opt_in.deposit(
            DepositArgs(
                payment=algorand_client.create_transaction.payment(
                    PaymentParams(
                        sender=account.address,
                        receiver=digital_marketplace_client.app_address,
                        amount=cst.AMOUNT_TO_DEPOSIT,
                    )
                )
            ),
            params=CommonAppCallParams(sender=account.address),
        )
    deposit_group.opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=bidder.address,
                    receiver=digital_marketplace_client.app_address,
                    amount=cst.AMOUNT_TO_DEPOSIT,
                )
            )
        ),
        params=CommonAppCallParams(sender=bidder.address),
    ).send(send_params=SendParams(populate_app_call_resources=True))


@pytest.fixture(scope="function")
def scenario_sponsor_asset(
    digital_marketplace_client: DigitalMarketplaceClient,
    scenario_deposit: Callable,
    seller: SigningAccount,
    asset_to_sell: int,
) -> None:
    digital_marketplace_client.send.sponsor_asset(
        SponsorAssetArgs(asset=asset_to_sell),
        params=CommonAppCallParams(
            extra_fee=AlgoAmount.from_micro_algo(1_000), sender=seller.address
        ),
    )


@pytest.fixture(scope="function")
def scenario_open_sale(
    digital_marketplace_client: DigitalMarketplaceClient,
    scenario_sponsor_asset: Callable,
    algorand_client: AlgorandClient,
    seller: SigningAccount,
    asset_to_sell: int,
) -> None:
    digital_marketplace_client.send.open_sale(
        OpenSaleArgs(
            asset_deposit=algorand_client.create_transaction.asset_transfer(
                AssetTransferParams(
                    sender=seller.address,
                    asset_id=asset_to_sell,
                    amount=cst.ASA_AMOUNT_TO_SELL,
                    receiver=digital_marketplace_client.app_address,
                )
            ),
            cost=cst.COST_TO_BUY.micro_algo,
        ),
        params=CommonAppCallParams(sender=seller.address),
        send_params=SendParams(populate_app_call_resources=True),
    )
