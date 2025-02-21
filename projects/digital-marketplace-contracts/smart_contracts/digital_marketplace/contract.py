from algopy import ARC4Contract, Global, LocalState, Txn, UInt64, gtxn
from algopy.arc4 import abimethod


class DigitalMarketplace(ARC4Contract):
    def __init__(self) -> None:
        self.deposited = LocalState(UInt64)

    @abimethod(allow_actions=["NoOp", "OptIn"])
    def deposit(self, payment: gtxn.PaymentTransaction) -> None:
        assert payment.sender == Txn.sender
        assert payment.receiver == Global.current_application_address

        self.deposited[Txn.sender] = (
            self.deposited.get(Txn.sender, UInt64(0)) + payment.amount
        )
