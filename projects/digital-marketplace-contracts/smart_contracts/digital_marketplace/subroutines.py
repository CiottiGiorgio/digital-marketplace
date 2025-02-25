from algopy import UInt64, arc4, subroutine, urange

from smart_contracts.digital_marketplace.contract import PlacedBid, SaleKey


@subroutine
def sales_box_mbr(prefix_length: UInt64) -> UInt64:
    # fmt: off
    return 2_500 + 400 * (
        # Domain separator
        prefix_length +
        # SaleKey
        32 + 8 +
        # Sale
        # Since the Sale type contains one dynamic type,
        #  it's got a 2 byte prefix pointing to that dynamic type
        2 +
        # amount & cost fields
        8 + 8 +
        # bid field is a dynamic array and so it has got a length prefix
        2 +
        # One optional Bid type
        (32 + 8)
    )
    # fmt: on


@subroutine
def placed_bids_box_mbr() -> UInt64:
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
def find_placed_bid(
    placed_bids: arc4.DynamicArray[PlacedBid], key: SaleKey
) -> tuple[bool, UInt64]:
    for i in urange(placed_bids.length):
        if placed_bids[i].sale_key == key:
            return True, i
    return False, UInt64(0)
