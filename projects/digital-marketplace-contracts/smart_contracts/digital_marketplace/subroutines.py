from algopy import ImmutableArray, UInt64, subroutine, urange

from smart_contracts.digital_marketplace.contract import BidReceipt, SaleKey


@subroutine
def sales_box_mbr(prefix_length: UInt64) -> UInt64:
    # fmt: off
    return 2_500 + 400 * (
        # Domain separator
        prefix_length +
        # SaleKey
        32 + 8 +
        # Sale
        # amount & cost fields
        8 + 8 +
        # bid field
        32 + 8
    )
    # fmt: on


@subroutine
def receipt_book_box_mbr() -> UInt64:
    return UInt64(
        2_500
        + 400
        * (
            # assuming it's possible to fill an entire box
            64
            + 32768
        )
    )


@subroutine
def find_bid_receipt(
    receipts: ImmutableArray[BidReceipt], key: SaleKey
) -> tuple[bool, UInt64]:
    for i in urange(receipts.length):
        if receipts[i].sale_key == key:
            return True, i
    return False, UInt64(0)
