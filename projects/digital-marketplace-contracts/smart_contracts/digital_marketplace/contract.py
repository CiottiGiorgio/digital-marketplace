from algopy import (
    ARC4Contract,
    Asset,
    BoxMap,
    Global,
    LocalState,
    Txn,
    UInt64,
    arc4,
    gtxn,
    itxn,
)
from algopy.arc4 import abimethod


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


class DigitalMarketplace(ARC4Contract):
    def __init__(self) -> None:
        self.deposited = LocalState(UInt64)

        self.sales = BoxMap(SaleKey, Sale)

    @abimethod(allow_actions=["NoOp", "OptIn"])
    def deposit(self, payment: gtxn.PaymentTransaction) -> None:
        assert payment.sender == Txn.sender
        assert payment.receiver == Global.current_application_address

        self.deposited[Txn.sender] = (
            self.deposited.get(Txn.sender, default=UInt64(0)) + payment.amount
        )

    @abimethod
    def sponsor_asset(self, asset: Asset) -> None:
        assert not Global.current_application_address.is_opted_in(asset)

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
        assert asset_deposit.sender == Txn.sender
        assert asset_deposit.asset_receiver == Global.current_application_address

        # FIXME: Subtract from self.deposited the amount to be locked for this box.

        self.sales[
            SaleKey(arc4.Address(Txn.sender), arc4.UInt64(asset_deposit.xfer_asset.id))
        ] = Sale(
            arc4.UInt64(asset_deposit.asset_amount), cost, arc4.DynamicArray[Bid]()
        )

    @abimethod
    def close_sale(self, sale_key: SaleKey) -> None:
        assert sale_key.owner.native == Txn.sender

        # FIXME: Add to self.deposited the amount locked for this box.

        sale = self.sales[sale_key].copy()

        itxn.AssetTransfer(
            xfer_asset=sale_key.asset.native,
            asset_receiver=Txn.sender,
            asset_amount=sale.amount.native,
        ).submit()

        del self.sales[sale_key]

    # TODO: Write a readonly method that returns the encumbered and unencumbered bids.
