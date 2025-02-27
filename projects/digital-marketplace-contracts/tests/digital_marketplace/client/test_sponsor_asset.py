from typing import Callable

import helpers
import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    LogicError,
    PaymentParams,
    SigningAccount,
)

import smart_contracts.digital_marketplace.errors as err
from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    DepositArgs,
    DigitalMarketplaceClient,
    SponsorAssetArgs,
)


@pytest.fixture(scope="function")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient, first_seller: SigningAccount
) -> DigitalMarketplaceClient:
    return digital_marketplace_client.clone(default_sender=first_seller.address)


def test_fail_already_opted_into_sponsor_asset(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_sponsor_asset: Callable,
    first_seller: SigningAccount,
) -> None:
    with pytest.raises(LogicError, match=err.ALREADY_OPTED_IN):
        dm_client.send.sponsor_asset(
            SponsorAssetArgs(asset=asset_to_sell),
            params=CommonAppCallParams(
                extra_fee=AlgoAmount.from_micro_algo(1_000),
            ),
        )


def test_fail_not_enough_deposited_sponsor_asset(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
) -> None:
    dm_client.send.opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=first_seller.address,
                    receiver=dm_client.app_address,
                    amount=AlgoAmount.from_algo(0),
                )
            )
        )
    )

    with pytest.raises(LogicError, match="- would result negative"):
        dm_client.send.sponsor_asset(SponsorAssetArgs(asset=asset_to_sell))


def test_pass_sponsor_asset(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_deposit: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
) -> None:
    deposited_before_call = dm_client.state.local_state(first_seller.address).deposited

    dm_client.send.sponsor_asset(
        SponsorAssetArgs(asset=asset_to_sell),
        params=CommonAppCallParams(
            sender=first_seller.address, extra_fee=AlgoAmount.from_micro_algo(1_000)
        ),
    )

    assert (
        dm_client.state.local_state(first_seller.address).deposited
        - deposited_before_call
        == -AlgoAmount.from_micro_algo(100_000).micro_algo
    )

    assert (
        helpers.asa_amount(
            algorand_client,
            dm_client.app_address,
            asset_to_sell,
        )
        == 0
    )
