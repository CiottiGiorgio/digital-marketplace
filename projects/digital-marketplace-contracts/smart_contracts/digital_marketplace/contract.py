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
    find_placed_bid,
    placed_bids_box_mbr,
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


class PlacedBid(arc4.Struct):
    sale_key: SaleKey
    bid_amount: arc4.UInt64


class UnencumberedBidsReceipt(arc4.Struct):
    total_bids: arc4.UInt64
    unencumbered_bids: arc4.UInt64


class DigitalMarketplace(ARC4Contract):
    def __init__(self) -> None:
        self.deposited = LocalState(UInt64)

        self.sales = BoxMap(SaleKey, Sale)
        self.placed_bids = BoxMap(arc4.Address, arc4.DynamicArray[PlacedBid])

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

        maybe_best_bid = self.sales[sale_key].bid.copy()
        if maybe_best_bid:
            assert (
                maybe_best_bid[0].amount.native < new_bid_amount.native
            ), err.WORSE_BID

            self.sales[sale_key].bid[0] = new_bid.copy()
        else:
            self.sales[sale_key].bid.append(new_bid.copy())

        new_placed_bid = PlacedBid(sale_key.copy(), new_bid_amount)
        if self.placed_bids.maybe(arc4_sender)[1]:
            found, index = find_placed_bid(
                self.placed_bids[arc4_sender].copy(), sale_key.copy()
            )
            if found:
                self.deposited[Txn.sender] += self.placed_bids[arc4_sender][
                    index
                ].bid_amount.native
                self.placed_bids[arc4_sender][index] = new_placed_bid.copy()
            else:
                self.placed_bids[arc4_sender].append(new_placed_bid.copy())
        else:
            self.deposited[Txn.sender] -= placed_bids_box_mbr()
            self.placed_bids[arc4_sender] = arc4.DynamicArray[PlacedBid](
                new_placed_bid.copy()
            )

        self.deposited[Txn.sender] -= new_bid_amount.native

    @subroutine
    def is_encumbered(self, bid: PlacedBid) -> bool:
        return not (
            not self.sales.maybe(bid.sale_key)[1]
            or not self.sales.maybe(bid.sale_key)[0].bid
            or not self.sales.maybe(bid.sale_key)[0].bid[0].bidder.native == Txn.sender
        )

    @abimethod(allow_actions=["NoOp", "OptIn"])
    def claim_unencumbered_bids(self) -> None:
        self.deposited[Txn.sender] = self.deposited.get(Txn.sender, UInt64(0))

        placed_bids = self.placed_bids[arc4.Address(Txn.sender)].copy()
        encumbered_placed_bids = arc4.DynamicArray[PlacedBid]()

        for i in urange(placed_bids.length):
            if not self.is_encumbered(placed_bids[i].copy()):
                self.deposited[Txn.sender] += placed_bids[i].bid_amount.native
            else:
                encumbered_placed_bids.append(placed_bids[i].copy())

        if encumbered_placed_bids:
            self.placed_bids[arc4.Address(Txn.sender)] = encumbered_placed_bids.copy()
        else:
            self.deposited[Txn.sender] += placed_bids_box_mbr()
            del self.placed_bids[arc4.Address(Txn.sender)]

    @abimethod(readonly=True)
    def get_total_and_unencumbered_bids(self) -> UnencumberedBidsReceipt:
        total_bids = UInt64(0)
        unencumbered_bids = UInt64(0)

        placed_bids = self.placed_bids[arc4.Address(Txn.sender)].copy()

        for i in urange(placed_bids.length):
            total_bids += placed_bids[i].bid_amount.native
            if not self.is_encumbered(placed_bids[i].copy()):
                unencumbered_bids += placed_bids[i].bid_amount.native

        return UnencumberedBidsReceipt(
            arc4.UInt64(total_bids), arc4.UInt64(unencumbered_bids)
        )

    @abimethod(allow_actions=["NoOp", "OptIn"])
    def accept_bid(self, asset: arc4.UInt64) -> None:
        sale_key = SaleKey(owner=arc4.Address(Txn.sender), asset=asset)
        sale = self.sales[sale_key].copy()
        current_best_bid = sale.bid[0].copy()

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
