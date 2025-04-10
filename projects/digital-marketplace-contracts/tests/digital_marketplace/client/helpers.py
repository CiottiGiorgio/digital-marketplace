import consts as cst
from algokit_utils import AlgoAmount, AlgorandClient


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


def receipt_book_mbr(n_receipts: int) -> AlgoAmount:
    """
    Returns the MBR of the receipt book box depending on how many receipts contains.
    """
    return (
        AlgoAmount(micro_algo=0)
        if not n_receipts
        else cst.RECEIPT_BOOK_BOX_BASE_MBR
        + AlgoAmount(
            micro_algo=n_receipts * cst.RECEIPT_BOOK_BOX_PER_RECEIPT_MBR.micro_algo
        )
    )
