import yaml

def get_log_files():
    log_files = []
    for i in range(4):
        log_files.append("/tmp/libra_swarm/logs/{}.log".format(i))
    return log_files

def get_urls():
    urls = []
    for i in range(4):
        with open("/tmp/libra_swarm/{}/node.yaml".format(i), 'r') as stream:
            urls.append("http://"+yaml.safe_load(stream)['json_rpc']['address'])
    return urls

def hotstuff_forensic_within_view(qc_1, qc_2):
    epoch_1 = qc_1["vote_data"]["proposed"]["epoch"]
    epoch_2 = qc_2["vote_data"]["proposed"]["epoch"]
    round_1 = qc_1["vote_data"]["proposed"]["round"]
    round_2 = qc_2["vote_data"]["proposed"]["round"]
    id_1 = qc_1["signed_ledger_info"]["V0"]["ledger_info"]["commit_info"]["id"]
    id_2 = qc_2["signed_ledger_info"]["V0"]["ledger_info"]["commit_info"]["id"]
    assert epoch_1 == epoch_2
    assert round_1 == round_2
    assert id_1 != id_2
    # omit the signature checking
    signers_1 = qc_1["signed_ledger_info"]["V0"]["signatures"]
    signers_2 = qc_2["signed_ledger_info"]["V0"]["signatures"]
    signers_1 = set(signers_1.keys())
    signers_2 = set(signers_2.keys())
    return signers_1.intersection(signers_2)

def hotstuff_forensic_across_views(qc_1, qc_2, pre_qc2_qcs):
    epoch_1 = qc_1["vote_data"]["proposed"]["epoch"]
    epoch_2 = qc_2["vote_data"]["proposed"]["epoch"]
    round_1 = qc_1["vote_data"]["proposed"]["round"]
    round_2 = qc_2["vote_data"]["proposed"]["round"]
    id_1 = qc_1["signed_ledger_info"]["V0"]["ledger_info"]["commit_info"]["id"]
    id_2 = qc_2["signed_ledger_info"]["V0"]["ledger_info"]["commit_info"]["id"]
    assert epoch_1 == epoch_2
    assert round_1 < round_2
    # omit checking pre_qc2_qcs is a valid chain of qc ending with qc_2
    # omit checking qc_1 and qc_2 are indeed in different branch
    # omit the signature checking
    signers_1 = qc_1["signed_ledger_info"]["V0"]["signatures"]
    round2qc = {}
    for _qc in pre_qc2_qcs:
        round2qc[_qc["vote_data"]["proposed"]["round"]] = _qc
    for i in range(round_1, round_2+1):
        if i in round2qc:
            _qc = round2qc[i]
            _round = _qc["vote_data"]["parent"]["round"]
            _id = _qc["vote_data"]["parent"]["id"]
            assert _round < round_1 or _round == round_1 and _id != id_1, "the first higher qc should violate safety voting rule"
            signers_2 = _qc["signed_ledger_info"]["V0"]["signatures"]
            signers_1 = set(signers_1.keys())
            signers_2 = set(signers_2.keys())
            return signers_1.intersection(signers_2)
    assert False, "should not reach here"