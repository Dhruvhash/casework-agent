"""Hackathon policy v1.0. Recommendations only; no banking actions execute."""
from decimal import Decimal


def exposure(transactions):
    return float(sum((abs(Decimal(str(t['amount_usd']))) for t in transactions), Decimal('0')).quantize(Decimal('.01')))


def route(action, amount):
    if action in {'FILE_REPORT', 'BLOCK_ALL_CARDS'} or action == 'BLOCK_CARD' and amount > 2500:
        return 'L2'
    if action in {'DECLINE_TRANSACTION', 'BLOCK_CARD'}:
        return 'L1'
    return 'auto'


def decide(probability, amount, *, response='pending', dispute=False, testing=False,
           cleared=False, shared_fraud=False, coordinated=False, conflict=False, recurring_verified=False,
           confirmed_cards=0, credentials_compromised=False):
    actions = []
    verdict, status = 'uncertain', 'open'
    def add(action, reason):
        if action not in {a['action'] for a in actions}:
            actions.append({'action': action, 'route': route(action, amount), 'reason': reason})
    if response == 'none' and probability <= .15 and not dispute and not conflict:
        verdict, status = 'legitimate', 'closed_legitimate'
        add('CLOSE_NO_FRAUD', 'Section 6: low suspicion with established amount, product and region history; retain the evidence trail.')
    elif response == 'confirmed':
        verdict, status, probability = 'legitimate', 'closed_legitimate', .05
        add('CLOSE_NO_FRAUD', 'R3: simulated customer confirmation settles the flagged transaction; no real reply was supplied.')
        if dispute:
            add('CREATE_CASE', '3a: preserve the disputed-charge investigation and verification trail.')
        if recurring_verified:
            add('WARN_CUSTOMER', 'R7: verified merchant, amount and monthly cadence match; explain recurring charge.')
    else:
        if response == 'denied':
            verdict, status, probability = 'fraud', 'closed_fraud', .95
            add('BLOCK_CARD', 'R2: simulated customer denial; recommended block requires human approval.')
            if confirmed_cards>=2 or credentials_compromised:
                add('BLOCK_ALL_CARDS','R10: independently confirmed compromise of two cards or customer credentials; L2 approval required.')
        elif response == 'no_reply_24h':
            add('MONITOR_CARD', 'R4: simulated absence of reply for 24 hours; monitor for 72 hours.')
            add('DECLINE_TRANSACTION', 'R4: recommend declining pending authorizations only; settlement status is not supplied.')
        else:
            add('VERIFY_WITH_CUSTOMER', 'R1/section 5: evidence does not settle authorization; request customer validation before blocking.')
        if testing:
            add('DECLINE_TRANSACTION', 'R5: three small online authorizations on a proven card within one hour precede a larger purchase.')
            add('STEP_UP_AUTH', 'R5: verify authorization after a card-testing sequence.')
            if cleared:
                add('BLOCK_CARD', 'R5: a purchase above $100 is independently confirmed cleared.')
        if recurring_verified and dispute:
            add('WARN_CUSTOMER', 'R7: confirmed same-merchant monthly pattern; explain charge and verify before blocking.')
        if probability >= .30 or dispute or response != 'none' or testing:
            add('CREATE_CASE', '3a: investigation requests evidence, handles a dispute, or has probability at least 0.30.')
        report = (verdict == 'fraud' or probability >= .85) and (amount > 1000 or shared_fraud or coordinated)
        if report:
            add('CREATE_CASE', '3a: every report requires an internal case.')
            add('FILE_REPORT', 'R2/R6/R9 and 3a: confirmed or strongly suspected fraud meets exposure or evidenced shared-abuse criteria; L2 approval required.')
        if shared_fraud:
            add('CREATE_CASE','R6: preserve confirmed shared-origin fraud evidence.')
            add('FILE_REPORT','R6: confirmed shared-origin fraud on several cards; L2 approval required.')
            add('MONITOR_CONNECTED_CARDS', 'R6: monitor other cards with evidenced fraud sharing the identified origin.')
        if coordinated:
            add('CREATE_CASE','R9: preserve evidenced coordinated abuse.')
            add('FILE_REPORT','R9: evidenced coordinated abuse requires L2 review of the report.')
        if (verdict == 'uncertain' and amount > 500) or conflict or coordinated:
            status = 'escalated'
            add('ESCALATE_TO_ANALYST', 'R8/R9: uncertainty with exposure above $500, conflicting evidence, or coordinated abuse needs analyst review.')
    return {'verdict': verdict, 'status': status, 'probability': probability, 'actions': actions}
