from collections import defaultdict
from utils import *
from sql import *
import pandas as pd
import numpy as np
import re
import time
import datetime
import json


nodes = ["node0", "node1", "node2", "node3", "twin0", "twin1"]
detected = -1
culprits = []
qcs = defaultdict(dict)
qcr = dict()
conflict = 0
commit1 = 0
commit2 = 0
prepare = -1

def check_across_view(r1, r2):
    global qcs
    qc_1 = None
    qc_2 = None
    pre_qc2_qcs = list()
    for _qc in qcs["2"].values():
        if _qc["vote_data"]["proposed"]["round"]==r1:
            qc_1=_qc
    for _qc in qcs["3"].values():
        if _qc["vote_data"]["proposed"]["round"]==r2:
            qc_2=_qc
    return hotstuff_forensic_across_views(qc_1,qc_2,[qc_2])


def check_round():
    global qcs, commit1, round_2, qcr
    qcs = defaultdict(dict) # block hash -> qc
    qc_pattern = re.compile(r'([0-9]+)-node-twins.*({"quorum_cert":.*})')

    libra_twins_forensic_log = './logs/libra_across.log'

    with open(libra_twins_forensic_log) as fin:
        for line in fin:
            m = qc_pattern.search(line)
            if m is not None:
                d = json.loads(m.group(2))
                r = d["quorum_cert"]["vote_data"]["proposed"]["round"] # round/view
                h = d["quorum_cert"]["vote_data"]["proposed"]["id"] # block hash/ proposed id
                grand_h = d["quorum_cert"]["signed_ledger_info"]["V0"]["ledger_info"]["commit_info"]["id"] # grandparent hash/ commit id
                qcs[m.group(1)][h]=d["quorum_cert"]
    qcr = dict()
    for i in range(6):
        a=str(i)
        for _qc in qcs[a].values():
            r = _qc["vote_data"]["proposed"]["round"]
            h = _qc["vote_data"]["proposed"]["id"]
            qcr[(i,r)] = h[:6]
    last = 0
    for _qc in qcs["2"].values():
        r = _qc["signed_ledger_info"]["V0"]["ledger_info"]["commit_info"]["round"]
        if r > 0 and r == last+1:
            last = r
        if r > 0 and r > last+1:
            commit1 = last + 2
            break
    for _qc in qcs["3"].values():
        r = _qc["signed_ledger_info"]["V0"]["ledger_info"]["commit_info"]["round"]
        if r > commit1:
            prepare = r
            commit2 = r+2
            break
    print(commit1, commit2, prepare)
    return commit1, commit2, prepare
        

def get_qcs_from_log(n):
    global qcs, conflict, detected, culprits, qcr, commit1, commit2, prepare
    twin_nodes = {}
    commit_qcs = defaultdict(dict) # block id -> grandparent id (the commit block)

    df_lst = list()
    start = n*4
    for r in range(start, start+4):
        rnd_lst = [r]
        if r == commit2:
            detected = r
            culprits = [x[:5] for x in check_across_view(commit1, prepare)]
            insert_culprits((r, "{}".format(culprits), commit1, commit2, prepare))
            conflict = 1
            clear_images(3)
        for i in range(6):
            if (i,r) in qcr:
                rnd_lst.append("'"+qcr[(i,r)]+"'")
            else:
                rnd_lst.append(' null ')
        df_lst.append(rnd_lst)
        insert_qcs_twins(tuple(rnd_lst))
        ts = time.time()
        timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        insert_conflict((timestamp, r, conflict))

    df = pd.DataFrame(np.array(df_lst), columns=['round', 'node0', 'node1', 'node2', 'node3', 'twin0', 'twin1']).to_dict('records')
    for node in nodes:
        insert_node(node, (df[0]['round'], "{}:<br>{}".format(df[0]['round'], df[0][node]), "{}:<br>{}".format(df[1]['round'],df[1][node]), "{}:<br>{}".format(df[2]['round'],df[2][node])))    
    return df


def update(n):
    print("update", n)
    if n > 0:
        #delete_qcs(4)
        for node in nodes:
            delete_node(node, 1)
    get_qcs_from_log(n)
    #get_logs()

if __name__ == "__main__":
    #log_files = get_log_files()
    #clear_text(nodes)
    clear_images(2)
    clear_qcs_twins()
    clear_conflict()
    clear_culprits()
    commit1, commit2, prepare = check_round()
    for node in nodes:
        clear_node(node)
    cnt = 0
    while True:
        if detected > -1: break
        update(cnt)
        time.sleep(5)
        cnt += 1
        