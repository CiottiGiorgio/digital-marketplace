from typing import Callable

import consts as cst
import helpers
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
    BuyArgs,
    DigitalMarketplaceClient,
    SaleKey,
)


@pytest.fixture(scope="function")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient, buyer: SigningAccount
) -> DigitalMarketplaceClient:
    return digital_marketplace_client.clone(default_sender=buyer.address)


def test_pass_buy(
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    algorand_client: AlgorandClient,
    buyer: SigningAccount,
    seller: SigningAccount,
    asset_to_sell: int,
) -> None:
    seller_deposited_before_call = dm_client.state.local_state(seller.address).deposited
    buyer_deposited_before_call = dm_client.state.local_state(buyer.address).deposited

    app_asa_balance = helpers.asa_amount(
        algorand_client, dm_client.app_address, asset_to_sell
    )
    buyer_asa_balance = helpers.asa_amount(
        algorand_client, buyer.address, asset_to_sell
    )

    dm_client.send.buy(
        BuyArgs(sale_key=SaleKey(owner=seller.address, asset=asset_to_sell)),
        params=CommonAppCallParams(extra_fee=AlgoAmount.from_micro_algo(1_000)),
        send_params=SendParams(populate_app_call_resources=True),
    )

    assert (
        dm_client.state.local_state(seller.address).deposited
        - seller_deposited_before_call
        == AlgoAmount.from_algo(cst.COST_TO_BUY).micro_algo
    )
    assert (
        dm_client.state.local_state(buyer.address).deposited
        - buyer_deposited_before_call
        == -AlgoAmount.from_algo(cst.COST_TO_BUY).micro_algo
    )
    assert (
        helpers.asa_amount(algorand_client, dm_client.app_address, asset_to_sell)
        - app_asa_balance
        == -cst.ASA_AMOUNT_TO_SELL
    )
    assert (
        helpers.asa_amount(algorand_client, buyer.address, asset_to_sell)
        - buyer_asa_balance
        == cst.ASA_AMOUNT_TO_SELL
    )

    with pytest.raises(AlgodHTTPError, match="box not found"):
        dm_client.state.box.sales.get_value(
            SaleKey(owner=seller.address, asset=asset_to_sell)
        )
