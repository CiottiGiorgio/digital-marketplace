from typing import Callable

import consts as cst
import helpers
import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AssetCreateParams,
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


def test_fail_clawback_sponsor_asset(
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
) -> None:
    result = algorand_client.send.asset_create(
        AssetCreateParams(
            sender=first_seller.address,
            total=cst.ASA_AMOUNT_TO_CREATE,
            decimals=cst.ASA_DECIMALS,
            clawback=first_seller.address,
        )
    )

    with pytest.raises(LogicError, match=err.CLAWBACK_ASA):
        dm_client.send.sponsor_asset(
            SponsorAssetArgs(asset=result.asset_id),
            params=CommonAppCallParams(extra_fee=AlgoAmount.from_micro_algo(1_000)),
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
