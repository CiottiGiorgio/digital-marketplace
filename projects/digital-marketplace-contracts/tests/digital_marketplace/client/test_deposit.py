import consts as cst
import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    LogicError,
    PaymentParams,
    SigningAccount,
)
from algosdk.atomic_transaction_composer import TransactionWithSigner

import smart_contracts.digital_marketplace.errors as err
from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    DepositArgs,
    DigitalMarketplaceClient,
)


def test_fail_diff_sender_opt_in_deposit(
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
    random_account: SigningAccount,
) -> None:
    """
    Test that an opt-in deposit fails if the sender of the payment transaction
    is different from the sender of the app call.
    """
    with pytest.raises(LogicError, match=err.DIFFERENT_SENDER):
        dm_client.send.opt_in.deposit(
            DepositArgs(
                payment=TransactionWithSigner(
                    txn=algorand_client.create_transaction.payment(
                        PaymentParams(
                            sender=random_account.address,
                            receiver=dm_client.app_address,
                            amount=AlgoAmount(algo=1),
                        )
                    ),
                    signer=random_account.signer,
                )
            ),
        )


def test_fail_wrong_receiver_opt_in_deposit(
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
) -> None:
    """
    Test that an opt-in deposit fails if the receiver of the payment transaction
    is not the digital marketplace application.
    """
    with pytest.raises(LogicError, match=err.WRONG_RECEIVER):
        dm_client.send.opt_in.deposit(
            DepositArgs(
                payment=TransactionWithSigner(
                    txn=algorand_client.create_transaction.payment(
                        PaymentParams(
                            sender=first_seller.address,
                            receiver=first_seller.address,
                            amount=AlgoAmount(algo=1),
                        )
                    ),
                    signer=first_seller.signer,
                )
            ),
        )


def test_pass_noop_and_opt_in_deposit(
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
) -> None:
    """
    Test that an opt-in deposit followed by a regular deposit succeeds and
    updates the local state of the first seller correctly.
    """
    dm_client.send.opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=first_seller.address,
                    receiver=dm_client.app_address,
                    amount=AlgoAmount(algo=1),
                )
            )
        )
    )

    assert (
        dm_client.state.local_state(first_seller.address).deposited
        == AlgoAmount(algo=1).micro_algo
    )

    dm_client.send.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=first_seller.address,
                    receiver=dm_client.app_address,
                    amount=cst.AMOUNT_TO_DEPOSIT - AlgoAmount(algo=1),
                )
            )
        )
    )

    assert (
        dm_client.state.local_state(first_seller.address).deposited
        == cst.AMOUNT_TO_DEPOSIT.micro_algo
    )
