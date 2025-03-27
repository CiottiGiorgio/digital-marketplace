from algopy import (
    ARC4Contract,
    Asset,
    BoxMap,
    Global,
    LocalState,
    OnCompleteAction,
    Txn,
    UInt64,
    arc4,
    gtxn,
    itxn,
    subroutine,
    urange,
)
from algopy.arc4 import abimethod

import smart_contracts.digital_marketplace.errors as err
from smart_contracts.digital_marketplace.subroutines import (
    find_bid_receipt,
    receipt_book_box_mbr,
    sales_box_mbr,
)


class SaleKey(arc4.Struct):
    owner: arc4.Address
    asset: arc4.UInt64


class Bid(arc4.Struct):
    bidder: arc4.Address
    amount: arc4.UInt64


class Sale(arc4.Struct):
    amount: arc4.UInt64
    cost: arc4.UInt64
    # Ideally we'd like to write:
    #  bid: Optional[Bid]
    # Since there's no Optional in Algorand Python, we use a DynamicArray that
    #  is either empty or contains exactly one element.
    # We need to be the ones that enforce this constraint.
    bid: arc4.DynamicArray[Bid]


class BidReceipt(arc4.Struct):
    sale_key: SaleKey
    amount: arc4.UInt64


class UnencumberedBidsReceipt(arc4.Struct):
    total_bids: arc4.UInt64
    unencumbered_bids: arc4.UInt64


class DigitalMarketplace(ARC4Contract):
    def __init__(self) -> None:
        self.deposited = LocalState(UInt64)

        self.sales = BoxMap(SaleKey, Sale)
        self.receipt_book = BoxMap(arc4.Address, arc4.DynamicArray[BidReceipt])

    @abimethod(allow_actions=["NoOp", "OptIn"])
    def deposit(self, payment: gtxn.PaymentTransaction) -> None:
        assert payment.sender == Txn.sender, err.DIFFERENT_SENDER
        assert (
            payment.receiver == Global.current_application_address
        ), err.WRONG_RECEIVER

        self.deposited[Txn.sender] = (
            self.deposited.get(Txn.sender, default=UInt64(0)) + payment.amount
        )

    @abimethod(allow_actions=["NoOp", "CloseOut"])
    def withdraw(self, amount: arc4.UInt64) -> None:
        if Txn.on_completion == OnCompleteAction.NoOp:
            self.deposited[Txn.sender] -= amount.native

            itxn.Payment(receiver=Txn.sender, amount=amount.native).submit()
        else:
            itxn.Payment(
                receiver=Txn.sender, amount=self.deposited[Txn.sender]
            ).submit()

    @abimethod
    def sponsor_asset(self, asset: Asset) -> None:
        assert not Global.current_application_address.is_opted_in(
            asset
        ), err.ALREADY_OPTED_IN
        assert asset.clawback == Global.zero_address, err.CLAWBACK_ASA

        self.deposited[Txn.sender] -= Global.asset_opt_in_min_balance

        itxn.AssetTransfer(
            xfer_asset=asset,
            asset_receiver=Global.current_application_address,
            asset_amount=0,
        ).submit()

    @abimethod
    def open_sale(
        self, asset_deposit: gtxn.AssetTransferTransaction, cost: arc4.UInt64
    ) -> None:
        assert asset_deposit.sender == Txn.sender, err.DIFFERENT_SENDER
        assert (
            asset_deposit.asset_receiver == Global.current_application_address
        ), err.WRONG_RECEIVER

        sale_key = SaleKey(
            arc4.Address(Txn.sender), arc4.UInt64(asset_deposit.xfer_asset.id)
        )
        assert not self.sales.maybe(sale_key)[1], err.SALE_ALREADY_EXISTS

        self.deposited[Txn.sender] -= sales_box_mbr(self.sales.key_prefix.length)

        self.sales[sale_key] = Sale(
            arc4.UInt64(asset_deposit.asset_amount), cost, arc4.DynamicArray[Bid]()
        )

    @abimethod(allow_actions=["NoOp", "OptIn"])
    def close_sale(self, asset: Asset) -> None:
        sale_key = SaleKey(arc4.Address(Txn.sender), arc4.UInt64(asset.id))

        itxn.AssetTransfer(
            xfer_asset=asset,
            asset_receiver=Txn.sender,
            asset_amount=self.sales[sale_key].amount.native,
        ).submit()

        self.deposited[Txn.sender] = self.deposited.get(
            Txn.sender, default=UInt64(0)
        ) + sales_box_mbr(self.sales.key_prefix.length)

        del self.sales[sale_key]

    @abimethod
    def buy(self, sale_key: SaleKey) -> None:
        assert Txn.sender != sale_key.owner.native, err.SELLER_CANT_BE_BUYER

        self.deposited[Txn.sender] -= self.sales[sale_key].cost.native
        self.deposited[sale_key.owner.native] += self.sales[
            sale_key
        ].cost.native + sales_box_mbr(self.sales.key_prefix.length)

        itxn.AssetTransfer(
            xfer_asset=sale_key.asset.native,
            asset_receiver=Txn.sender,
            asset_amount=self.sales[sale_key].amount.native,
        ).submit()

        del self.sales[sale_key]

    @abimethod
    def bid(self, sale_key: SaleKey, new_bid_amount: arc4.UInt64) -> None:
        arc4_sender = arc4.Address(Txn.sender)
        new_bid = Bid(bidder=arc4_sender, amount=new_bid_amount)

        assert arc4_sender != sale_key.owner, err.SELLER_CANT_BE_BIDDER

        maybe_best_bid = self.sales[sale_key].bid.copy()
        if maybe_best_bid:
            assert (
                maybe_best_bid[0].amount.native < new_bid_amount.native
            ), err.WORSE_BID

            self.sales[sale_key].bid[0] = new_bid.copy()
        else:
            self.sales[sale_key].bid.append(new_bid.copy())

        new_bid_receipt = BidReceipt(sale_key.copy(), new_bid_amount)
        if self.receipt_book.maybe(arc4_sender)[1]:
            found, index = find_bid_receipt(
                self.receipt_book[arc4_sender].copy(), sale_key.copy()
            )
            if found:
                self.deposited[Txn.sender] += self.receipt_book[arc4_sender][
                    index
                ].amount.native
                self.receipt_book[arc4_sender][index] = new_bid_receipt.copy()
            else:
                self.receipt_book[arc4_sender].append(new_bid_receipt.copy())
        else:
            self.deposited[Txn.sender] -= receipt_book_box_mbr()
            self.receipt_book[arc4_sender] = arc4.DynamicArray[BidReceipt](
                new_bid_receipt.copy()
            )

        self.deposited[Txn.sender] -= new_bid_amount.native

    @subroutine
    def is_encumbered(self, bid: BidReceipt) -> bool:
        return (
            self.sales.maybe(bid.sale_key)[1]
            and bool(self.sales.maybe(bid.sale_key)[0].bid)
            and self.sales.maybe(bid.sale_key)[0].bid[0].bidder.native == Txn.sender
        )

    @abimethod(allow_actions=["NoOp", "OptIn"])
    def claim_unencumbered_bids(self) -> None:
        self.deposited[Txn.sender] = self.deposited.get(Txn.sender, UInt64(0))

        receipt_book = self.receipt_book[arc4.Address(Txn.sender)].copy()
        encumbered_receipts = arc4.DynamicArray[BidReceipt]()

        for i in urange(receipt_book.length):
            if self.is_encumbered(receipt_book[i].copy()):
                encumbered_receipts.append(receipt_book[i].copy())
            else:
                self.deposited[Txn.sender] += receipt_book[i].amount.native

        if encumbered_receipts:
            self.receipt_book[arc4.Address(Txn.sender)] = encumbered_receipts.copy()
        else:
            self.deposited[Txn.sender] += receipt_book_box_mbr()
            del self.receipt_book[arc4.Address(Txn.sender)]

    @abimethod(readonly=True)
    def get_total_and_unencumbered_bids(self) -> UnencumberedBidsReceipt:
        total_bids = UInt64(0)
        unencumbered_bids = UInt64(0)

        if self.receipt_book.maybe(arc4.Address(Txn.sender))[1]:
            receipt_book = self.receipt_book[arc4.Address(Txn.sender)].copy()

            for i in urange(receipt_book.length):
                total_bids += receipt_book[i].amount.native
                if not self.is_encumbered(receipt_book[i].copy()):
                    unencumbered_bids += receipt_book[i].amount.native

        return UnencumberedBidsReceipt(
            arc4.UInt64(total_bids), arc4.UInt64(unencumbered_bids)
        )

    @abimethod(allow_actions=["NoOp", "OptIn"])
    def accept_bid(self, asset: arc4.UInt64) -> None:
        sale_key = SaleKey(owner=arc4.Address(Txn.sender), asset=asset)
        sale = self.sales[sale_key].copy()
        current_best_bid = sale.bid[0].copy()

        receipt_book = self.receipt_book[current_best_bid.bidder].copy()
        found, index = find_bid_receipt(receipt_book.copy(), sale_key)
        assert found

        encumbered_receipts = arc4.DynamicArray[BidReceipt]()
        for i in urange(receipt_book.length):
            if i != index:
                encumbered_receipts.append(receipt_book[i].copy())

        if encumbered_receipts:
            self.receipt_book[current_best_bid.bidder] = encumbered_receipts.copy()
        else:
            self.deposited[current_best_bid.bidder.native] += receipt_book_box_mbr()
            del self.receipt_book[current_best_bid.bidder]

        self.deposited[Txn.sender] = (
            self.deposited.get(Txn.sender, default=UInt64(0))
            + current_best_bid.amount.native
            + sales_box_mbr(self.sales.key_prefix.length)
        )
        itxn.AssetTransfer(
            xfer_asset=asset.native,
            asset_receiver=current_best_bid.bidder.native,
            asset_amount=sale.amount.native,
        ).submit()

        del self.sales[sale_key]
