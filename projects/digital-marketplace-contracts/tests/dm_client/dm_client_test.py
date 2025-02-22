import consts as cst
import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AssetTransferParams,
    CommonAppCallParams,
    PaymentParams,
    SendParams,
    SigningAccount,
)

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    CloseSaleArgs,
    DepositArgs,
    DigitalMarketplaceClient,
    OpenSaleArgs,
    Sale,
    SaleKey,
    SponsorAssetArgs,
)


@pytest.mark.parametrize("actor_name", ["seller", "buyer", "bidder"])
def test_opt_in_deposit(
    digital_marketplace_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    actor_name: str,
    request: pytest.FixtureRequest,
) -> None:
    actor: SigningAccount = request.getfixturevalue(actor_name)

    dm_client = digital_marketplace_client.clone(default_sender=actor.address)
    result = dm_client.send.opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=actor.address,
                    signer=actor.signer,
                    receiver=dm_client.app_address,
                    amount=AlgoAmount.from_algo(1),
                )
            )
        )
    )
    assert result.confirmation

    assert (
        dm_client.state.local_state(actor.address).deposited
        == AlgoAmount.from_algo(1).micro_algo
    )


@pytest.mark.parametrize("actor_name", ["seller", "buyer", "bidder"])
def test_noop_deposit(
    digital_marketplace_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    actor_name: str,
    request: pytest.FixtureRequest,
) -> None:
    actor: SigningAccount = request.getfixturevalue(actor_name)

    dm_client = digital_marketplace_client.clone(default_sender=actor.address)
    result = dm_client.send.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=actor.address,
                    receiver=dm_client.app_address,
                    amount=AlgoAmount.from_algo(cst.AMOUNT_TO_DEPOSIT - 1),
                )
            )
        )
    )
    assert result.confirmation

    assert (
        dm_client.state.local_state(actor.address).deposited
        == AlgoAmount.from_algo(cst.AMOUNT_TO_DEPOSIT).micro_algo
    )


def test_sponsor_asset(
    digital_marketplace_client: DigitalMarketplaceClient,
    seller: SigningAccount,
    asset_to_sell: int,
) -> None:
    dm_client = digital_marketplace_client.clone(default_sender=seller.address)

    deposited_before_call = dm_client.state.local_state(seller.address).deposited

    dm_client.send.sponsor_asset(
        SponsorAssetArgs(asset=asset_to_sell),
        params=CommonAppCallParams(extra_fee=AlgoAmount.from_micro_algo(1_000)),
    )

    assert (
        dm_client.state.local_state(seller.address).deposited - deposited_before_call
        == -AlgoAmount.from_micro_algo(100_000).micro_algo
    )


def test_open_sale(
    digital_marketplace_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    seller: SigningAccount,
    asset_to_sell: int,
) -> None:
    dm_client = digital_marketplace_client.clone(default_sender=seller.address)

    mbr_before_call = algorand_client.account.get_information(
        dm_client.app_address
    ).min_balance
    asa_balance_before_call = next(
        filter(
            lambda x: x["asset-id"] == asset_to_sell,
            algorand_client.account.get_information(dm_client.app_address).assets,
        )
    )["amount"]
    deposited_before_call = dm_client.state.local_state(seller.address).deposited

    dm_client.send.open_sale(
        OpenSaleArgs(
            asset_deposit=algorand_client.create_transaction.asset_transfer(
                AssetTransferParams(
                    sender=seller.address,
                    asset_id=asset_to_sell,
                    receiver=dm_client.app_address,
                    amount=cst.ASA_AMOUNT_TO_SELL,
                )
            ),
            cost=AlgoAmount.from_algo(cst.COST_TO_BUY).micro_algo,
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )

    asa_balance = next(
        filter(
            lambda x: x["asset-id"] == asset_to_sell,
            algorand_client.account.get_information(dm_client.app_address).assets,
        )
    )["amount"]

    # The created box does not contain a bid yet.
    # The mbr does not raise as much as the subtracted amount from the deposit.
    assert algorand_client.account.get_information(
        dm_client.app_address
    ).min_balance.micro_algo - mbr_before_call.micro_algo == 2_500 + 400 * (
        5 + 32 + 8 + 2 + 8 + 8 + 2
    )
    assert asa_balance - asa_balance_before_call == cst.ASA_AMOUNT_TO_SELL
    assert dm_client.state.local_state(
        seller.address
    ).deposited - deposited_before_call == -(
        2_500 + 400 * (5 + 32 + 8 + 2 + 8 + 8 + 2 + 32 + 8)
    )

    assert dm_client.state.box.sales.get_value(
        SaleKey(owner=seller.address, asset=asset_to_sell)
    ) == Sale(
        cst.ASA_AMOUNT_TO_SELL, AlgoAmount.from_algo(cst.COST_TO_BUY).micro_algo, []
    )


def test_close_sale(
    digital_marketplace_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    seller: SigningAccount,
    asset_to_sell: int,
) -> None:
    dm_client = digital_marketplace_client.clone(default_sender=seller.address)

    mbr_before_call = algorand_client.account.get_information(
        dm_client.app_address
    ).min_balance
    asa_balance_before_call = next(
        filter(
            lambda x: x["asset-id"] == asset_to_sell,
            algorand_client.account.get_information(dm_client.app_address).assets,
        )
    )["amount"]
    deposited_before_call = dm_client.state.local_state(seller.address).deposited

    dm_client.send.close_sale(
        CloseSaleArgs(sale_key=SaleKey(owner=seller.address, asset=asset_to_sell)),
        params=CommonAppCallParams(extra_fee=AlgoAmount.from_micro_algo(1_000)),
        send_params=SendParams(populate_app_call_resources=True),
    )

    asa_balance = next(
        filter(
            lambda x: x["asset-id"] == asset_to_sell,
            algorand_client.account.get_information(dm_client.app_address).assets,
        )
    )["amount"]

    # The created box does not contain a bid yet.
    # The mbr does not raise as much as the subtracted amount from the deposit.
    assert algorand_client.account.get_information(
        dm_client.app_address
    ).min_balance.micro_algo - mbr_before_call.micro_algo == -(
        2_500 + 400 * (5 + 32 + 8 + 2 + 8 + 8 + 2)
    )
    assert asa_balance - asa_balance_before_call == -cst.ASA_AMOUNT_TO_SELL
    assert dm_client.state.local_state(
        seller.address
    ).deposited - deposited_before_call == 2_500 + 400 * (
        5 + 32 + 8 + 2 + 8 + 8 + 2 + 32 + 8
    )
