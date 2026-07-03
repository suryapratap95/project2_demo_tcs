"""Hand-written QA pairs grounded in data/knowledge_base/, covering every
source document and the main intent categories. Used by run_eval.py to
measure retrieval, answer, and end-to-end quality.
"""

EVAL_DATASET = [
    {
        "id": "savings-mab",
        "category": "account_inquiry",
        "question": "What is the minimum average monthly balance required for a savings account in an urban branch?",
        "ground_truth": "Rs. 5,000 per month for urban branches (Rs. 2,000 for rural branches); a penalty of Rs. 100/month applies if not maintained.",
        "expected_source": "faq_general.html",
    },
    {
        "id": "fd-premature-withdrawal",
        "category": "account_inquiry",
        "question": "If I withdraw my fixed deposit before maturity, what penalty will I pay?",
        "ground_truth": "A penalty of 1% on the applicable interest rate for premature withdrawal.",
        "expected_source": "faq_general.html",
    },
    {
        "id": "fd-senior-citizen-rate",
        "category": "account_inquiry",
        "question": "How much extra interest do senior citizens get on fixed deposits?",
        "ground_truth": "An additional 0.50% per annum over the standard FD rate on all tenures.",
        "expected_source": "savings_account_faq.html",
    },
    {
        "id": "nomination-requirement",
        "category": "general_faq",
        "question": "Is nomination mandatory for new savings accounts?",
        "ground_truth": "Yes, nomination is mandatory for all new savings accounts and fixed deposits opened after January 2023.",
        "expected_source": "savings_account_faq.html",
    },
    {
        "id": "home-loan-salaried-income",
        "category": "loan_query",
        "question": "What is the minimum monthly income required for a salaried applicant to be eligible for a home loan?",
        "ground_truth": "A minimum net monthly income of Rs. 25,000, with at least 2 years of continuous employment.",
        "expected_source": "home_loan_policy.docx",
    },
    {
        "id": "home-loan-prepayment-penalty",
        "category": "loan_query",
        "question": "Is there a prepayment penalty on a floating rate home loan?",
        "ground_truth": "No, there is no prepayment or foreclosure penalty on floating-rate home loans for individual borrowers, per RBI guidelines.",
        "expected_source": "home_loan_policy.docx",
    },
    {
        "id": "card-dispute-provisional-credit",
        "category": "card_dispute",
        "question": "If I'm charged twice for the same online purchase, how quickly will I get provisional credit?",
        "ground_truth": "Provisional credit is issued within 10 working days of the dispute being logged, pending investigation.",
        "expected_source": "card_dispute_policy.pdf",
    },
    {
        "id": "card-dispute-zero-liability-window",
        "category": "card_dispute",
        "question": "Within how many days must I report an unauthorized card transaction to have zero liability?",
        "ground_truth": "Within 3 working days of receiving the transaction alert, provided there was no customer negligence.",
        "expected_source": "card_dispute_policy.pdf",
    },
    {
        "id": "neft-charge-50000",
        "category": "general_faq",
        "question": "How much does a branch-initiated NEFT transfer of Rs 50,000 cost?",
        "ground_truth": "Rs. 4 plus GST, since Rs. 50,000 falls in the Rs. 10,001 to Rs. 1,00,000 slab.",
        "expected_source": "upi_neft_charges.csv",
    },
    {
        "id": "upi-p2p-charge",
        "category": "general_faq",
        "question": "Is there a charge for UPI person-to-person payments?",
        "ground_truth": "No, UPI person-to-person payments are free with no charges under NPCI UPI guidelines.",
        "expected_source": "upi_neft_charges.csv",
    },
]
