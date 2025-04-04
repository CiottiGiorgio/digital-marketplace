from algokit_utils import AlgorandClient


def asa_amount(algorand_client: AlgorandClient, account: str, asset_id: int) -> int:
    """
    Retrieve the amount of a specific Algorand Standard Asset (ASA) held by an account.
    """
    return next(
        filter(
            lambda x: x["asset-id"] == asset_id,
            algorand_client.account.get_information(account).assets,
        )
    )["amount"]
