from typing import Callable

from algosdk.error import AlgodHTTPError
import consts as cst
import helpers
import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AssetOptInParams,
    AssetTransferParams,
    CommonAppCallParams,
    PaymentParams,
    SendParams,
    SigningAccount,
)

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    BuyArgs,
    DepositArgs,
    DigitalMarketplaceClient,
    OpenSaleArgs,
    SaleKey,
    SponsorAssetArgs,
)


@pytest.fixture(scope="function")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient, buyer: SigningAccount
) -> DigitalMarketplaceClient:
    return digital_marketplace_client.clone(default_sender=buyer.address)


@pytest.fixture(scope="function")
def open_a_sale_and_buyer_deposit(
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    seller: SigningAccount,
    buyer: SigningAccount,
    asset_to_sell: int,
) -> None:
    seller_dm_client = dm_client.clone(default_sender=seller.address)

    seller_dm_client.new_group().opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=seller.address,
                    receiver=dm_client.app_address,
                    amount=AlgoAmount.from_algo(cst.AMOUNT_TO_DEPOSIT),
                )
            )
        )
    ).sponsor_asset(
        SponsorAssetArgs(asset=asset_to_sell),
        params=CommonAppCallParams(extra_fee=AlgoAmount.from_micro_algo(1_000)),
    ).open_sale(
        OpenSaleArgs(
            asset_deposit=algorand_client.create_transaction.asset_transfer(
                AssetTransferParams(
                    sender=seller.address,
                    asset_id=asset_to_sell,
                    amount=cst.ASA_AMOUNT_TO_SELL,
                    receiver=dm_client.app_address,
                )
            ),
            cost=AlgoAmount.from_algo(cst.COST_TO_BUY).micro_algo,
        )
    ).send(
        send_params=SendParams(populate_app_call_resources=True)
    )

    dm_client.new_group().opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=buyer.address,
                    receiver=dm_client.app_address,
                    amount=AlgoAmount.from_algo(cst.AMOUNT_TO_DEPOSIT),
                )
            )
        )
    ).add_transaction(
        txn=algorand_client.create_transaction.asset_opt_in(
            AssetOptInParams(sender=buyer.address, asset_id=asset_to_sell)
        )
    ).send()


def test_pass_buy(
    dm_client: DigitalMarketplaceClient,
    open_a_sale_and_buyer_deposit: Callable,
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
