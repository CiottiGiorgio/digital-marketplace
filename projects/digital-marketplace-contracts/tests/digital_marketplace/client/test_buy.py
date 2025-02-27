from typing import Callable

import consts as cst
import helpers
import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AssetOptInParams,
    CommonAppCallParams,
    LogicError,
    PaymentParams,
    SendParams,
    SigningAccount,
)
from algosdk.error import AlgodHTTPError

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    BuyArgs,
    DepositArgs,
    DigitalMarketplaceClient,
    SaleKey,
)


@pytest.fixture(scope="function")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient, buyer: SigningAccount
) -> DigitalMarketplaceClient:
    return digital_marketplace_client.clone(default_sender=buyer.address)


def test_fail_not_enough_deposited_buy(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
    random_account: SigningAccount,
) -> None:
    dm_client.new_group().add_transaction(
        algorand_client.create_transaction.asset_opt_in(
            AssetOptInParams(sender=random_account.address, asset_id=asset_to_sell)
        )
    ).opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=random_account.address,
                    receiver=dm_client.app_address,
                    amount=cst.AMOUNT_TO_BID - AlgoAmount(micro_algo=1),
                )
            )
        ),
        params=CommonAppCallParams(sender=random_account.address),
    ).send()

    with pytest.raises(LogicError, match="- would result negative"):
        dm_client.send.buy(
            BuyArgs(sale_key=SaleKey(owner=first_seller.address, asset=asset_to_sell)),
            params=CommonAppCallParams(
                extra_fee=AlgoAmount(micro_algo=1_000),
                sender=random_account.address,
            ),
            send_params=SendParams(populate_app_call_resources=True),
        )


def test_pass_buy(
    asset_to_sell: int,
    dm_client: DigitalMarketplaceClient,
    scenario_open_sale: Callable,
    algorand_client: AlgorandClient,
    buyer: SigningAccount,
    first_seller: SigningAccount,
) -> None:
    seller_deposited_before_call = dm_client.state.local_state(
        first_seller.address
    ).deposited
    buyer_deposited_before_call = dm_client.state.local_state(buyer.address).deposited

    app_asa_balance = helpers.asa_amount(
        algorand_client, dm_client.app_address, asset_to_sell
    )
    buyer_asa_balance = helpers.asa_amount(
        algorand_client, buyer.address, asset_to_sell
    )

    dm_client.send.buy(
        BuyArgs(sale_key=SaleKey(owner=first_seller.address, asset=asset_to_sell)),
        params=CommonAppCallParams(extra_fee=AlgoAmount(micro_algo=1_000)),
        send_params=SendParams(populate_app_call_resources=True),
    )

    assert (
        dm_client.state.local_state(first_seller.address).deposited
        - seller_deposited_before_call
        == cst.COST_TO_BUY.micro_algo + cst.SALES_BOX_MBR.micro_algo
    )
    assert (
        dm_client.state.local_state(buyer.address).deposited
        - buyer_deposited_before_call
        == -cst.COST_TO_BUY.micro_algo
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
            SaleKey(owner=first_seller.address, asset=asset_to_sell)
        )
