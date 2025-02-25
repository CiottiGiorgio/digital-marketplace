from typing import Callable

import consts as cst
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


def test_fail_already_opted_into_sponsor_asset(
    dm_client: DigitalMarketplaceClient,
    deposit_into_dm: Callable,
    random_account: SigningAccount,
    asset_to_sell: int,
) -> None:
    dm_client.send.sponsor_asset(
        SponsorAssetArgs(asset=asset_to_sell),
        params=CommonAppCallParams(
            sender=random_account.address,
            extra_fee=AlgoAmount.from_micro_algo(1_000),
        ),
    )

    with pytest.raises(LogicError, match=err.ALREADY_OPTED_IN):
        dm_client.send.sponsor_asset(
            SponsorAssetArgs(asset=asset_to_sell),
            params=CommonAppCallParams(
                sender=random_account.address,
                extra_fee=AlgoAmount.from_micro_algo(1_000),
            ),
        )


def test_fail_not_enough_deposited_sponsor_asset(
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
        dm_client.send.sponsor_asset(SponsorAssetArgs(asset=asset_to_sell))


def test_pass_sponsor_asset(
    dm_client: DigitalMarketplaceClient,
    deposit_into_dm: Callable,
    algorand_client: AlgorandClient,
    random_account: SigningAccount,
    asset_to_sell: int,
) -> None:
    deposited_before_call = dm_client.state.local_state(
        random_account.address
    ).deposited

    dm_client.send.sponsor_asset(
        SponsorAssetArgs(asset=asset_to_sell),
        params=CommonAppCallParams(
            sender=random_account.address, extra_fee=AlgoAmount.from_micro_algo(1_000)
        ),
    )

    assert (
        dm_client.state.local_state(random_account.address).deposited
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
