from scripts.agent.policy import decide, exposure, route


def names(result):
    return {a['action'] for a in result['actions']}


def test_risk_alone_does_not_block():
    assert 'BLOCK_CARD' not in names(decide(.99, 20))


def test_report_and_route_boundaries():
    assert 'FILE_REPORT' not in names(decide(.5, 1000, response='denied'))
    assert 'FILE_REPORT' in names(decide(.5, 1000.01, response='denied'))
    assert route('BLOCK_CARD', 2500) == 'L1'
    assert route('BLOCK_CARD', 2500.01) == 'L2'


def test_uncertain_escalation_threshold():
    assert decide(.5, 500)['status'] == 'open'
    assert decide(.5, 500.01)['status'] == 'escalated'


def test_confirmation_clears_despite_high_trigger():
    r = decide(.99, 9000, response='confirmed')
    assert r['verdict'] == 'legitimate'
    assert names(r) == {'CLOSE_NO_FRAUD'}


def test_money_absolute_decimal():
    assert exposure([{'amount_usd': '-0.10'}, {'amount_usd': '0.20'}]) == .30


def test_testing_does_not_invent_settlement():
    assert 'BLOCK_CARD' not in names(decide(.65, 120, testing=True))
