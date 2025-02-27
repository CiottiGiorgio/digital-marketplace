from typing import Callable

import consts as cst
import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    SendParams,
    SigningAccount,
)
from algosdk.error import AlgodHTTPError

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    AcceptBidArgs,
    DigitalMarketplaceClient,
    SaleKey,
)
from tests.digital_marketplace.client import helpers


@pytest.fixture(scope="function")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient, first_seller: SigningAccount
) -> DigitalMarketplaceClient:
    return digital_marketplace_client.clone(default_sender=first_seller.address)


def test_pass_accept_bid(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_first_seller_first_bidder_bid: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
    first_bidder: SigningAccount,
) -> None:
    sale_key = SaleKey(owner=first_seller.address, asset=asset_to_sell)

    assert dm_client.state.box.sales.get_value(sale_key).bid == [
        [first_bidder.address, cst.AMOUNT_TO_BID.micro_algo]
    ]
    deposited_before_call = dm_client.state.local_state(first_seller.address).deposited
    asa_balance_before_call = helpers.asa_amount(
        algorand_client,
        first_bidder.address,
        asset_to_sell,
    )

    dm_client.send.accept_bid(
        AcceptBidArgs(asset=asset_to_sell),
        params=CommonAppCallParams(extra_fee=AlgoAmount.from_micro_algo(1_000)),
        send_params=SendParams(populate_app_call_resources=True),
    )

    with pytest.raises(AlgodHTTPError, match="box not found"):
        _ = dm_client.state.box.sales.get_value(sale_key)
    assert (
        dm_client.state.local_state(first_seller.address).deposited
        - deposited_before_call
        == (cst.AMOUNT_TO_BID + cst.SALES_BOX_MBR).micro_algo
    )
    assert (
        helpers.asa_amount(
            algorand_client,
            first_bidder.address,
            asset_to_sell,
        )
        - asa_balance_before_call
        == cst.ASA_AMOUNT_TO_SELL
    )
