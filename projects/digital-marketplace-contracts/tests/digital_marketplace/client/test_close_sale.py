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
    CloseSaleArgs,
    DigitalMarketplaceClient,
    SaleKey,
)


def test_pass_noop_close_sale(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
) -> None:
    mbr_before_call = algorand_client.account.get_information(
        dm_client.app_address
    ).min_balance
    asa_balance_before_call = helpers.asa_amount(
        algorand_client,
        dm_client.app_address,
        asset_to_sell,
    )
    deposited_before_call = dm_client.state.local_state(first_seller.address).deposited

    dm_client.send.close_sale(
        CloseSaleArgs(asset=asset_to_sell),
        params=CommonAppCallParams(extra_fee=AlgoAmount.from_micro_algo(1_000)),
        send_params=SendParams(populate_app_call_resources=True),
    )

    asa_balance = helpers.asa_amount(
        algorand_client,
        dm_client.app_address,
        asset_to_sell,
    )

    # The created box does not contain a bid yet.
    # The mbr does not raise as much as the subtracted amount from the deposit.
    assert (
        algorand_client.account.get_information(dm_client.app_address).min_balance
        - mbr_before_call
    ).micro_algo == -cst.SALES_BOX_BASE_MBR.micro_algo
    assert asa_balance - asa_balance_before_call == -cst.ASA_AMOUNT_TO_SELL
    assert (
        dm_client.state.local_state(first_seller.address).deposited
        - deposited_before_call
        == cst.SALES_BOX_MBR.micro_algo
    )

    with pytest.raises(AlgodHTTPError, match="box not found"):
        dm_client.state.box.sales.get_value(
            SaleKey(owner=first_seller.address, asset=asset_to_sell)
        )


def test_pass_opt_in_close_sale(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
) -> None:
    dm_client.send.clear_state()

    mbr_before_call = algorand_client.account.get_information(
        dm_client.app_address
    ).min_balance
    asa_balance_before_call = helpers.asa_amount(
        algorand_client,
        dm_client.app_address,
        asset_to_sell,
    )

    dm_client.send.opt_in.close_sale(
        CloseSaleArgs(asset=asset_to_sell),
        params=CommonAppCallParams(extra_fee=AlgoAmount.from_micro_algo(1_000)),
        send_params=SendParams(populate_app_call_resources=True),
    )

    asa_balance = helpers.asa_amount(
        algorand_client,
        dm_client.app_address,
        asset_to_sell,
    )

    # The created box does not contain a bid yet.
    # The mbr does not raise as much as the subtracted amount from the deposit.
    assert algorand_client.account.get_information(
        dm_client.app_address
    ).min_balance.micro_algo - mbr_before_call.micro_algo == -(
        cst.SALES_BOX_BASE_MBR.micro_algo
    )
    assert asa_balance - asa_balance_before_call == -cst.ASA_AMOUNT_TO_SELL
    assert (
        dm_client.state.local_state(first_seller.address).deposited
        == cst.SALES_BOX_MBR.micro_algo
    )

    with pytest.raises(AlgodHTTPError, match="box not found"):
        dm_client.state.box.sales.get_value(
            SaleKey(owner=first_seller.address, asset=asset_to_sell)
        )
