import consts as cst
import pytest
from algokit_utils import (
    AlgorandClient,
    LogicError,
    PaymentParams,
    SendParams,
    SigningAccount,
)
from algosdk.atomic_transaction_composer import TransactionWithSigner

import smart_contracts.digital_marketplace.errors as err
from smart_contracts.artifacts.digital_marketplace.digital_marketplace_client import (
    DepositArgs,
    DigitalMarketplaceClient,
)


def test_fail_diff_sender_deposit(
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
        dm_client.send.deposit(
            DepositArgs(
                payment=TransactionWithSigner(
                    txn=algorand_client.create_transaction.payment(
                        PaymentParams(
                            sender=random_account.address,
                            receiver=dm_client.app_address,
                            amount=cst.AMOUNT_TO_DEPOSIT,
                        )
                    ),
                    signer=random_account.signer,
                )
            ),
            send_params=SendParams(populate_app_call_resources=True),
        )


def test_fail_wrong_receiver_deposit(
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
) -> None:
    """
    Test that an opt-in deposit fails if the receiver of the payment transaction
    is not the digital marketplace application.
    """
    with pytest.raises(LogicError, match=err.WRONG_RECEIVER):
        dm_client.send.deposit(
            DepositArgs(
                payment=TransactionWithSigner(
                    txn=algorand_client.create_transaction.payment(
                        PaymentParams(
                            sender=first_seller.address,
                            receiver=first_seller.address,
                            amount=cst.AMOUNT_TO_DEPOSIT,
                        )
                    ),
                    signer=first_seller.signer,
                )
            ),
            send_params=SendParams(populate_app_call_resources=True),
        )


def test_pass_deposit(
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
) -> None:
    """
    Test that a deposit updates the <deposited> BoxMap of the first seller correctly.
    """
    dm_client.send.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=first_seller.address,
                    receiver=dm_client.app_address,
                    amount=cst.AMOUNT_TO_DEPOSIT,
                )
            )
        ),
        send_params=SendParams(populate_app_call_resources=True),
    )

    assert (
        dm_client.state.box.deposited.get_value(first_seller.address)
        == cst.RESIDUAL_INITIAL_DEPOSIT.micro_algo
    )
