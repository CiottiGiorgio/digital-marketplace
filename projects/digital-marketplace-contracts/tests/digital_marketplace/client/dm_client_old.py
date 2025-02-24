import consts as cst
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    SendParams,
    SigningAccount,
)

from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    CloseSaleArgs,
    DigitalMarketplaceClient,
    SaleKey,
)


def test_close_sale(
    digital_marketplace_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    random_account: SigningAccount,
    asset_to_sell: int,
) -> None:
    digital_marketplace_client = digital_marketplace_client.clone(
        default_sender=random_account.address
    )

    mbr_before_call = algorand_client.account.get_information(
        dm_client.app_address
    ).min_balance
    asa_balance_before_call = next(
        filter(
            lambda x: x["asset-id"] == asset_to_sell,
            algorand_client.account.get_information(dm_client.app_address).assets,
        )
    )["amount"]
    deposited_before_call = dm_client.state.local_state(
        random_account.address
    ).deposited

    dm_client.send.close_sale(
        CloseSaleArgs(
            sale_key=SaleKey(owner=random_account.address, asset=asset_to_sell)
        ),
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
        random_account.address
    ).deposited - deposited_before_call == 2_500 + 400 * (
        5 + 32 + 8 + 2 + 8 + 8 + 2 + 32 + 8
    )
