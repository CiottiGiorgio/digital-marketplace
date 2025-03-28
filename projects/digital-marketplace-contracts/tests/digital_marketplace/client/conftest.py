"""
Pytest fixtures for testing the Digital Marketplace application.

This module establishes a testing framework that navigates a critical distinction between:

1. Pytest fixture scope/lifetime - Controlling when fixtures are recreated between tests.
   - 'session' scope: For resources that can safely persist across test runs (accounts, assets)
   - 'function' scope: For fresh instances needed each test to avoid state contamination

2. Blockchain object lifecycle - The actual state of objects on the ledger.
   - Even with a 'function' scoped fixture, a client might reuse an existing app on the ledger
     if .deploy() is called and no changes are detected, inheriting previous state
   - Each test modifies the blockchain state with app calls, making reuse of app fixtures
     between tests problematic

Key fixtures include:
- Account fixtures (deployer, sellers, buyers, bidders)
- Asset creation and distribution
- Contract deployment (using .create.bare() to ensure fresh instances)
- Test scenarios to cover all crucial unit tests for the contract

These fixtures enable isolated testing of marketplace interactions while accounting for
the persistence of blockchain state between test runs.
"""

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
from numpy import random
from numpy.random import Generator

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    AcceptBidArgs,
    BidArgs,
    BuyArgs,
    DepositArgs,
    DigitalMarketplaceClient,
    DigitalMarketplaceFactory,
    OpenSaleArgs,
    SaleKey,
    SponsorAssetArgs,
)


@pytest.fixture(scope="session")
def rng(worker_id: str) -> Generator:
    return random.default_rng(list(worker_id.encode()))


@pytest.fixture(scope="session")
def deployer(rng: Generator, algorand_client: AlgorandClient) -> SigningAccount:
    """
    Fixture to provide the deployer account, ensuring it is funded.
    """
    account = algorand_client.account.from_environment("DEPLOYER")
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=cst.AMOUNT_TO_FUND,
        note=rng.integers(2**32).tobytes(),
    )
    return account


@pytest.fixture(scope="session")
def first_seller(rng: Generator, algorand_client: AlgorandClient) -> SigningAccount:
    """
    Fixture to provide the first seller account, ensuring it is funded.
    """
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=cst.AMOUNT_TO_FUND,
        note=rng.integers(2**32).tobytes(),
    )
    return account


@pytest.fixture(scope="session")
def second_seller(rng: Generator, algorand_client: AlgorandClient) -> SigningAccount:
    """
    Fixture to provide the second seller account, ensuring it is funded.
    """
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=cst.AMOUNT_TO_FUND,
        note=rng.integers(2**32).tobytes(),
    )
    return account


@pytest.fixture(scope="session")
def buyer(rng: Generator, algorand_client: AlgorandClient) -> SigningAccount:
    """
    Fixture to provide the buyer account, ensuring it is funded.
    """
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=cst.AMOUNT_TO_FUND,
        note=rng.integers(2**32).tobytes(),
    )
    return account


@pytest.fixture(scope="session")
def first_bidder(rng: Generator, algorand_client: AlgorandClient) -> SigningAccount:
    """
    Fixture to provide the first bidder account, ensuring it is funded.
    """
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=cst.AMOUNT_TO_FUND,
        note=rng.integers(2**32).tobytes(),
    )
    return account


@pytest.fixture(scope="session")
def second_bidder(rng: Generator, algorand_client: AlgorandClient) -> SigningAccount:
    """
    Fixture to provide the second bidder account, ensuring it is funded.
    """
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=cst.AMOUNT_TO_FUND,
        note=rng.integers(2**32).tobytes(),
    )
    return account


@pytest.fixture(scope="function")
def random_account(rng: Generator, algorand_client: AlgorandClient) -> SigningAccount:
    """
    Fixture to provide a random account, ensuring it is funded.
    """
    account = algorand_client.account.random()
    algorand_client.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=cst.AMOUNT_TO_FUND,
        note=rng.integers(2**32).tobytes(),
    )
    return account


@pytest.fixture(scope="session")
def asset_to_sell(
    rng: Generator,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
    second_seller: SigningAccount,
    buyer: SigningAccount,
    first_bidder: SigningAccount,
    second_bidder: SigningAccount,
) -> int:
    """
    Fixture to create an asset and opt-in necessary accounts.
    """
    result = algorand_client.send.asset_create(
        AssetCreateParams(
            sender=first_seller.address,
            total=2 * cst.ASA_AMOUNT_TO_CREATE,
            decimals=cst.ASA_DECIMALS,
            note=rng.integers(2**32).tobytes(),
        ),
    )
    algorand_client.new_group().add_asset_opt_in(
        AssetOptInParams(sender=second_seller.address, asset_id=result.asset_id)
    ).add_asset_transfer(
        AssetTransferParams(
            sender=first_seller.address,
            asset_id=result.asset_id,
            amount=cst.ASA_AMOUNT_TO_CREATE,
            receiver=second_seller.address,
            note=rng.integers(2**32).tobytes(),
        )
    ).add_asset_opt_in(
        AssetOptInParams(
            sender=buyer.address,
            asset_id=result.asset_id,
            note=rng.integers(2**32).tobytes(),
        )
    ).add_asset_opt_in(
        AssetOptInParams(
            sender=first_bidder.address,
            asset_id=result.asset_id,
            note=rng.integers(2**32).tobytes(),
        )
    ).add_asset_opt_in(
        AssetOptInParams(
            sender=second_bidder.address,
            asset_id=result.asset_id,
            note=rng.integers(2**32).tobytes(),
        )
    ).send()

    return result.asset_id


@pytest.fixture(scope="function")
def digital_marketplace_client(
    rng: Generator, algorand_client: AlgorandClient, deployer: SigningAccount
) -> DigitalMarketplaceClient:
    """
    Fixture providing a fresh DigitalMarketplaceClient instance using .create.bare() to ensure
    a new application is created on the ledger with each test.
    """
    factory = algorand_client.client.get_typed_app_factory(
        DigitalMarketplaceFactory, default_sender=deployer.address
    )

    client, _ = factory.send.create.bare(
        params=CommonAppCallParams(
            note=rng.integers(2**32).tobytes(),
        )
    )
    algorand_client.account.ensure_funded(
        client.app_address,
        dispenser_account=algorand_client.account.dispenser_from_environment(),
        min_spending_balance=AlgoAmount(algo=0),
        note=rng.integers(2**32).tobytes(),
    )
    return client


@pytest.fixture(scope="function")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient, first_seller: SigningAccount
) -> DigitalMarketplaceClient:
    """
    Fixture to provide a cloned DigitalMarketplaceClient instance with the first seller as the default sender.
    """
    return digital_marketplace_client.clone(default_sender=first_seller.address)


@pytest.fixture(scope="function")
def scenario_deposit(
    rng: Generator,
    digital_marketplace_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
    second_seller: SigningAccount,
    buyer: SigningAccount,
    first_bidder: SigningAccount,
    second_bidder: SigningAccount,
) -> None:
    """
    In this scenario, the following accounts deposit funds into the digital marketplace:
    - first_seller
    - second_seller
    - buyer
    - first_bidder
    - second_bidder
    """
    deposit_group = digital_marketplace_client.new_group()
    for account in [first_seller, second_seller, buyer, first_bidder, second_bidder]:
        deposit_group = deposit_group.opt_in.deposit(
            DepositArgs(
                payment=algorand_client.create_transaction.payment(
                    PaymentParams(
                        sender=account.address,
                        receiver=digital_marketplace_client.app_address,
                        amount=cst.AMOUNT_TO_DEPOSIT,
                        note=rng.integers(2**32).tobytes(),
                    )
                )
            ),
            params=CommonAppCallParams(sender=account.address),
        )
    deposit_group.send(send_params=SendParams(populate_app_call_resources=True))


@pytest.fixture(scope="function")
def scenario_sponsor_asset(
    rng: Generator,
    asset_to_sell: int,
    digital_marketplace_client: DigitalMarketplaceClient,
    scenario_deposit: Callable,
    first_seller: SigningAccount,
) -> None:
    """
    In this scenario, the first seller sponsors an asset after depositing funds.
    This is based on the 'scenario_deposit'.
    """
    digital_marketplace_client.send.sponsor_asset(
        SponsorAssetArgs(asset=asset_to_sell),
        params=CommonAppCallParams(
            note=rng.integers(2**32).tobytes(),
            extra_fee=AlgoAmount(micro_algo=1_000),
            sender=first_seller.address,
        ),
    )


@pytest.fixture(scope="function")
def scenario_open_sale(
    rng: Generator,
    asset_to_sell: int,
    digital_marketplace_client: DigitalMarketplaceClient,
    scenario_sponsor_asset: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
    second_seller: SigningAccount,
) -> None:
    """
    In this scenario, the sequence of events is:
    1. The first seller opens a sale for the asset.
    2. The second seller opens a sale for the asset.
    This is based on the 'scenario_sponsor_asset'.
    """
    digital_marketplace_client.new_group().open_sale(
        OpenSaleArgs(
            asset_deposit=algorand_client.create_transaction.asset_transfer(
                AssetTransferParams(
                    sender=first_seller.address,
                    asset_id=asset_to_sell,
                    amount=cst.ASA_AMOUNT_TO_SELL,
                    receiver=digital_marketplace_client.app_address,
                )
            ),
            cost=cst.COST_TO_BUY.micro_algo,
        ),
        params=CommonAppCallParams(
            sender=first_seller.address,
            note=rng.integers(2**32).tobytes(),
        ),
    ).open_sale(
        OpenSaleArgs(
            asset_deposit=algorand_client.create_transaction.asset_transfer(
                AssetTransferParams(
                    sender=second_seller.address,
                    asset_id=asset_to_sell,
                    amount=cst.ASA_AMOUNT_TO_SELL,
                    receiver=digital_marketplace_client.app_address,
                )
            ),
            cost=cst.COST_TO_BUY.micro_algo,
        ),
        params=CommonAppCallParams(
            sender=second_seller.address,
            note=rng.integers(2**32).tobytes(),
        ),
    ).send(
        send_params=SendParams(populate_app_call_resources=True)
    )


@pytest.fixture(scope="function")
def scenario_first_seller_first_bidder_bid(
    rng: Generator,
    asset_to_sell: int,
    digital_marketplace_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    """
    In this scenario, the sequence of events is:
    1. The first seller opens a sale.
    2. The first bidder places a bid on the sale.
    This is based on the 'scenario_open_sale'.
    """
    digital_marketplace_client.send.bid(
        BidArgs(
            sale_key=SaleKey(owner=first_seller.address, asset=asset_to_sell),
            new_bid_amount=cst.AMOUNT_TO_BID.micro_algo,
        ),
        params=CommonAppCallParams(
            sender=first_bidder.address,
            note=rng.integers(2**32).tobytes(),
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )


@pytest.fixture(scope="function")
def scenario_first_seller_second_bidder_outbid(
    rng: Generator,
    asset_to_sell: int,
    digital_marketplace_client: DigitalMarketplaceClient,
    scenario_first_seller_first_bidder_bid: Callable,
    first_seller: SigningAccount,
    second_bidder: SigningAccount,
) -> None:
    """
    In this scenario, the sequence of events is:
    1. The first seller opens a sale.
    2. The first bidder places a bid.
    3. The second bidder places a higher bid, outbidding the first bidder.
    This is based on the 'scenario_first_seller_first_bidder_bid'.
    """
    digital_marketplace_client.send.bid(
        BidArgs(
            sale_key=SaleKey(owner=first_seller.address, asset=asset_to_sell),
            new_bid_amount=cst.AMOUNT_TO_OUTBID.micro_algo,
        ),
        params=CommonAppCallParams(
            sender=second_bidder.address,
            note=rng.integers(2**32).tobytes(),
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )


@pytest.fixture(scope="function")
def scenario_accept_first_bid(
    rng: Generator,
    asset_to_sell: int,
    digital_marketplace_client: DigitalMarketplaceClient,
    scenario_first_seller_first_bidder_bid: Callable,
    first_seller: SigningAccount,
) -> None:
    """
    In this scenario, the sequence of events is:
    1. The first seller opens a sale.
    2. The first bidder places a bid.
    3. The first seller accepts the bid.
    This is based on the 'scenario_first_seller_first_bidder_bid'.
    """
    digital_marketplace_client.send.accept_bid(
        AcceptBidArgs(asset=asset_to_sell),
        params=CommonAppCallParams(
            extra_fee=AlgoAmount(micro_algo=1_000),
            sender=first_seller.address,
            note=rng.integers(2**32).tobytes(),
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )


@pytest.fixture(scope="function")
def scenario_first_bid_buy_both_sales(
    asset_to_sell: int,
    digital_marketplace_client: DigitalMarketplaceClient,
    scenario_first_seller_first_bidder_bid: Callable,
    first_seller: SigningAccount,
    second_seller: SigningAccount,
    buyer: SigningAccount,
) -> None:
    """
    In this scenario, the sequence of events is:
    1. The first seller opens a sale.
    2. The second seller opens a sale.
    3. The first bidder places a bid on the first seller's sale.
    4. The buyer buys both sales.
    This is based on the 'scenario_first_seller_first_bidder_bid'.
    """
    digital_marketplace_client.new_group().buy(
        BuyArgs(sale_key=SaleKey(owner=first_seller.address, asset=asset_to_sell)),
        params=CommonAppCallParams(
            extra_fee=AlgoAmount(micro_algo=1_000), sender=buyer.address
        ),
    ).buy(
        BuyArgs(sale_key=SaleKey(owner=second_seller.address, asset=asset_to_sell)),
        params=CommonAppCallParams(
            extra_fee=AlgoAmount(micro_algo=1_000), sender=buyer.address
        ),
    ).send(
        send_params=SendParams(populate_app_call_resources=True)
    )
