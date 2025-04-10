from algokit_utils import AlgoAmount

AMOUNT_TO_FUND = AlgoAmount(algo=1_000_000)
AMOUNT_TO_DEPOSIT = AlgoAmount(algo=50)
assert AMOUNT_TO_DEPOSIT.algo > 1

ASA_AMOUNT_TO_CREATE = 100_000
ASA_DECIMALS = 3
ASA_AMOUNT_TO_SELL = 2_000
COST_TO_BUY = AlgoAmount(algo=5)

AMOUNT_TO_BID = AlgoAmount(algo=4)
AMOUNT_TO_OUTBID = AMOUNT_TO_BID + AlgoAmount(micro_algo=1)

# Box Prefix
DEPOSITED_PREFIX = "deposited"
SALES_PREFIX = "sales"
RECEIPT_BOOK = "receipt_book"

# Box MBR
DEPOSITED_BOX_MBR = AlgoAmount(
    micro_algo=2_500 + 400 * (len(DEPOSITED_PREFIX) + 32 + 8)
)
SALES_BOX_MBR = AlgoAmount(
    micro_algo=2_500 + 400 * (len(SALES_PREFIX) + 32 + 8 + 8 + 8 + 32 + 8)
)
RECEIPT_BOOK_BOX_BASE_MBR = AlgoAmount(
    micro_algo=2_500 + 400 * (len(RECEIPT_BOOK) + 32 + 2)
)
RECEIPT_BOOK_BOX_PER_RECEIPT_MBR = AlgoAmount(micro_algo=400 * (32 + 8 + 8))

# Frequently used expressions
RESIDUAL_INITIAL_DEPOSIT = AMOUNT_TO_DEPOSIT - DEPOSITED_BOX_MBR
