import pytest
from algokit_utils import (
    AlgoAmount,
    CommonAppCallParams,
    AlgorandClient,
    PaymentParams,
    SigningAccount,
)
import consts as cst

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    DigitalMarketplaceClient,
    SponsorAssetArgs,
    DepositArgs,
)
from tests.conftest import algorand_client


@pytest.fixture(scope="module")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    seller: SigningAccount,
) -> DigitalMarketplaceClient:
    client = digital_marketplace_client.clone(default_sender=seller.address)
    client.send.opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=seller.address,
                    receiver=client.app_address,
                    amount=AlgoAmount.from_algo(cst.AMOUNT_TO_DEPOSIT),
                )
            )
        )
    )
    return client


def test_sponsor_asset(
    dm_client: DigitalMarketplaceClient,
    seller: SigningAccount,
    asset_to_sell: int,
) -> None:
    deposited_before_call = dm_client.state.local_state(seller.address).deposited

    dm_client.send.sponsor_asset(
        SponsorAssetArgs(asset=asset_to_sell),
        params=CommonAppCallParams(extra_fee=AlgoAmount.from_micro_algo(1_000)),
    )

    assert (
        dm_client.state.local_state(seller.address).deposited - deposited_before_call
        == -AlgoAmount.from_micro_algo(100_000).micro_algo
    )
