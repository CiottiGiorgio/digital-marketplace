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


@pytest.fixture(scope="function")
def dm_client(
    digital_marketplace_client: DigitalMarketplaceClient, first_seller: SigningAccount
) -> DigitalMarketplaceClient:
    return digital_marketplace_client.clone(default_sender=first_seller.address)


def test_fail_diff_sender_opt_in_deposit(
    dm_client: DigitalMarketplaceClient,
    algorand_client: AlgorandClient,
    first_seller: SigningAccount,
    random_account: SigningAccount,
) -> None:
    with pytest.raises(LogicError, match=err.DIFFERENT_SENDER):
        dm_client.send.opt_in.deposit(
            DepositArgs(
                payment=TransactionWithSigner(
                    txn=algorand_client.create_transaction.payment(
                        PaymentParams(
                            sender=random_account.address,
                            receiver=dm_client.app_address,
                            amount=AlgoAmount.from_algo(1),
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
    with pytest.raises(LogicError, match=err.WRONG_RECEIVER):
        dm_client.send.opt_in.deposit(
            DepositArgs(
                payment=TransactionWithSigner(
                    txn=algorand_client.create_transaction.payment(
                        PaymentParams(
                            sender=first_seller.address,
                            receiver=first_seller.address,
                            amount=AlgoAmount.from_algo(1),
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
    dm_client.send.opt_in.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=first_seller.address,
                    receiver=dm_client.app_address,
                    amount=AlgoAmount.from_algo(1),
                )
            )
        )
    )

    assert (
        dm_client.state.local_state(first_seller.address).deposited
        == AlgoAmount.from_algo(1).micro_algo
    )

    dm_client.send.deposit(
        DepositArgs(
            payment=algorand_client.create_transaction.payment(
                PaymentParams(
                    sender=first_seller.address,
                    receiver=dm_client.app_address,
                    amount=cst.AMOUNT_TO_DEPOSIT - AlgoAmount.from_algo(1),
                )
            )
        )
    )

    assert (
        dm_client.state.local_state(first_seller.address).deposited
        == cst.AMOUNT_TO_DEPOSIT.micro_algo
    )
