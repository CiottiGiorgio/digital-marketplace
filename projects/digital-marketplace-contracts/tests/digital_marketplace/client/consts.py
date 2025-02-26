from algokit_utils import AlgoAmount

AMOUNT_TO_FUND = AlgoAmount.from_algo(1_000_000)
AMOUNT_TO_DEPOSIT = AlgoAmount.from_algo(50)
assert AMOUNT_TO_DEPOSIT.algo > 1

ASA_AMOUNT_TO_CREATE = 100_000
ASA_DECIMALS = 3
ASA_AMOUNT_TO_SELL = 2_000
COST_TO_BUY = AlgoAmount.from_algo(5)

AMOUNT_TO_BID = AlgoAmount.from_algo(4)
AMOUNT_TO_OUTBID = AMOUNT_TO_BID + AlgoAmount.from_micro_algo(1)

# Box MBR
SALES_BOX_BASE_MBR = AlgoAmount.from_micro_algo(
    2_500 + 400 * (5 + 32 + 8 + 2 + 8 + 8 + 2)
)
SALES_BOX_OPTIONAL_MBR = AlgoAmount.from_micro_algo(400 * (32 + 8))
SALES_BOX_MBR = SALES_BOX_BASE_MBR + SALES_BOX_OPTIONAL_MBR
PLACED_BIDS_BOX_MBR = AlgoAmount.from_micro_algo(2_500 + 400 * (64 + 32_768))
