from algopy import ImmutableArray, UInt64, subroutine, urange

from smart_contracts.digital_marketplace.contract import BidReceipt, SaleKey


@subroutine
def find_bid_receipt(
    receipts: ImmutableArray[BidReceipt], key: SaleKey
) -> tuple[bool, UInt64]:
    for i in urange(receipts.length):
        if receipts[i].sale_key == key:
            return True, i
    return False, UInt64(0)
