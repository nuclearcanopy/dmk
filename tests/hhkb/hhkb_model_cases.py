"""Shared expectations for the Python and standalone browser target checks."""
MODELS = ('AHUX01',)


def model_cases():
    cases = {}
    for color in 'BWY':
        for blank in ('', 'N'):
            for suffix in ('', 'S', 'SC', 'SC1', 'SC2', 'SC12'):
                cases[f'PD-KB800{color}{blank}{suffix}'] = 'AHUX01'
    # Other HHKB families are not supported targets.
    for number in ('', 'unknown', 'PD-ID100B', 'PD-KB400WS', 'PD-KB420W',
                   'PD-KB401W', 'PD-KB401WN', 'PD-KB401WSC', 'PD-KB401YSC',
                   'PD-KB421W', 'PD-KB421BSC', 'PD-KB820YNS', 'PD-KB820WSC1',
                   'PD-KB401Y', 'PD-KB401WS', 'PD-KB401WSCX',
                   'PD-KB800', 'PD-KB800ZSC', 'PD-KB800YSC1X', 'PD-KB800YSC-1',
                   'PD-KB800YSC1 extra', 'PD-KB800YSS', 'PD-KB820WSC1X',
                   'PD-KB800W/PD-KB820W', 'PD-KB800WSC1\nPD-KB820WSC1'):
        cases[number] = None
    return cases
