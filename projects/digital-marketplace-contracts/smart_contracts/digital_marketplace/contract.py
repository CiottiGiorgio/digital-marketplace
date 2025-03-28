import typing

from algopy import (
    Account,
    ARC4Contract,
    Asset,
    BoxMap,
    Global,
    ImmutableArray,
    LocalState,
    OnCompleteAction,
    Txn,
    UInt64,
    arc4,
    gtxn,
    itxn,
    subroutine,
)
from algopy.arc4 import abimethod

import smart_contracts.digital_marketplace.errors as err
from smart_contracts.digital_marketplace.subroutines import (
    find_bid_receipt,
    receipt_book_box_mbr,
    sales_box_mbr,
)


class SaleKey(arc4.Struct, frozen=True):
    owner: arc4.Address
    asset: arc4.UInt64


class Bid(arc4.Struct, frozen=True):
    bidder: arc4.Address
    amount: arc4.UInt64


class Sale(arc4.Struct, frozen=True):
    amount: arc4.UInt64
    cost: arc4.UInt64
    # Ideally we'd like to write:
    #  bid: Optional[Bid]
    # Since there's no Optional in Algorand Python, we use the truthiness of bid.bidder
    # to know if a bid is present
    bid: Bid


class BidReceipt(arc4.Struct, frozen=True):
    sale_key: SaleKey
    amount: arc4.UInt64


class UnencumberedBidsReceipt(typing.NamedTuple):
    total_bids: UInt64
    unencumbered_bids: UInt64


class DigitalMarketplace(ARC4Contract):
    def __init__(self) -> None:
        self.deposited = LocalState(UInt64)

        self.sales = BoxMap(SaleKey, Sale)
        self.receipt_book = BoxMap(Account, ImmutableArray[BidReceipt])

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
        assert sale_key not in self.sales, err.SALE_ALREADY_EXISTS

        self.deposited[Txn.sender] -= sales_box_mbr(self.sales.key_prefix.length)

        self.sales[sale_key] = Sale(
            arc4.UInt64(asset_deposit.asset_amount),
            cost,
            Bid(arc4.Address(), arc4.UInt64()),
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
        new_bid = Bid(bidder=arc4.Address(Txn.sender), amount=new_bid_amount)

        assert Txn.sender != sale_key.owner, err.SELLER_CANT_BE_BIDDER

        sale = self.sales[sale_key]
        if sale.bid.bidder:
            assert sale.bid.amount.native < new_bid_amount.native, err.WORSE_BID

        self.sales[sale_key] = sale._replace(bid=new_bid)

        new_bid_receipt = BidReceipt(sale_key, new_bid_amount)
        receipt_book, exists = self.receipt_book.maybe(Txn.sender)
        if exists:
            found, index = find_bid_receipt(receipt_book, sale_key)
            if found:
                self.deposited[Txn.sender] += receipt_book[index].amount.native
                self.receipt_book[Txn.sender] = receipt_book.replace(
                    index, new_bid_receipt
                )
            else:
                self.receipt_book[Txn.sender] = receipt_book.append(new_bid_receipt)
        else:
            self.deposited[Txn.sender] -= receipt_book_box_mbr()
            self.receipt_book[Txn.sender] = ImmutableArray(new_bid_receipt)

        self.deposited[Txn.sender] -= new_bid_amount.native

    @subroutine
    def is_encumbered(self, bid: BidReceipt) -> bool:
        sale, exists = self.sales.maybe(bid.sale_key)
        return exists and bool(sale.bid.bidder) and sale.bid.bidder == Txn.sender

    @abimethod(allow_actions=["NoOp", "OptIn"])
    def claim_unencumbered_bids(self) -> None:
        self.deposited[Txn.sender] = self.deposited.get(Txn.sender, UInt64(0))

        encumbered_receipts = ImmutableArray[BidReceipt]()

        for receipt in self.receipt_book[Txn.sender]:
            if self.is_encumbered(receipt):
                encumbered_receipts = encumbered_receipts.append(receipt)
            else:
                self.deposited[Txn.sender] += receipt.amount.native

        if encumbered_receipts:
            self.receipt_book[Txn.sender] = encumbered_receipts
        else:
            self.deposited[Txn.sender] += receipt_book_box_mbr()
            del self.receipt_book[Txn.sender]

    @abimethod(readonly=True)
    def get_total_and_unencumbered_bids(self) -> UnencumberedBidsReceipt:
        total_bids = UInt64(0)
        unencumbered_bids = UInt64(0)

        receipt_book, exists = self.receipt_book.maybe(Txn.sender)
        if exists:
            for receipt in receipt_book:
                total_bids += receipt.amount.native
                if not self.is_encumbered(receipt):
                    unencumbered_bids += receipt.amount.native

        return UnencumberedBidsReceipt(total_bids, unencumbered_bids)

    @abimethod(allow_actions=["NoOp", "OptIn"])
    def accept_bid(self, asset: arc4.UInt64) -> None:
        sale_key = SaleKey(owner=arc4.Address(Txn.sender), asset=asset)
        sale = self.sales[sale_key]
        current_best_bid = sale.bid
        current_best_bidder = current_best_bid.bidder.native

        receipt_book = self.receipt_book[current_best_bidder]
        found, index = find_bid_receipt(receipt_book, sale_key)
        assert found

        encumbered_receipts = ImmutableArray[BidReceipt]()
        for receipt in receipt_book:
            if receipt != receipt_book[index]:
                encumbered_receipts = encumbered_receipts.append(receipt)

        if encumbered_receipts:
            self.receipt_book[current_best_bidder] = encumbered_receipts
        else:
            self.deposited[current_best_bidder] += receipt_book_box_mbr()
            del self.receipt_book[current_best_bidder]

        self.deposited[Txn.sender] = (
            self.deposited.get(Txn.sender, default=UInt64(0))
            + current_best_bid.amount.native
            + sales_box_mbr(self.sales.key_prefix.length)
        )
        itxn.AssetTransfer(
            xfer_asset=asset.native,
            asset_receiver=current_best_bidder,
            asset_amount=sale.amount.native,
        ).submit()

        del self.sales[sale_key]
