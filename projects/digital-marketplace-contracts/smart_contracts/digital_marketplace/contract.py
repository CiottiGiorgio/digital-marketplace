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
)
from algopy.arc4 import abimethod

import smart_contracts.digital_marketplace.errors as err


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

    @subroutine
    def sales_box_mbr(self) -> UInt64:
        # fmt: off
        return 2_500 + 400 * (
            # Domain separator
            self.sales.key_prefix.length +
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
        if Txn.on_completion == OnCompleteAction.CloseOut:
            assert self.deposited[Txn.sender] == amount.native, err.BALANCE_NOT_EMPTY

        self.deposited[Txn.sender] -= amount.native

        itxn.Payment(receiver=Txn.sender, amount=amount.native).submit()

    @abimethod
    def sponsor_asset(self, asset: Asset) -> None:
        assert not Global.current_application_address.is_opted_in(
            asset
        ), err.ALREADY_OPTED_IN

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

        self.deposited[Txn.sender] -= self.sales_box_mbr()

        self.sales[
            SaleKey(arc4.Address(Txn.sender), arc4.UInt64(asset_deposit.xfer_asset.id))
        ] = Sale(
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

        self.deposited[Txn.sender] = (
            self.deposited.get(Txn.sender, default=UInt64(0)) + self.sales_box_mbr()
        )

        del self.sales[sale_key]

    @abimethod
    def buy(self, sale_key: SaleKey) -> None:
        self.deposited[Txn.sender] -= self.sales[sale_key].cost.native
        self.deposited[sale_key.owner.native] += self.sales[sale_key].cost.native

        itxn.AssetTransfer(
            xfer_asset=sale_key.asset.native,
            asset_receiver=Txn.sender,
            asset_amount=self.sales[sale_key].amount.native,
        ).submit()

        del self.sales[sale_key]

    # TODO: Write a readonly method that returns the encumbered and unencumbered bids.
