import requests
import json
import threading
from utils import *
from sql import *
import os
import time
latest_round = -1
headers = {'content-type': 'application/json'}
get_latest_round_payload = {
	"method": "forensic_get_latest_round",
	"params": [],
	"jsonrpc": "2.0",
	"id": 0,
}
nodes = ["node0", "node1", "node2", "node3"]
cnt = 0


def get_qcs_from_rpc(urls):
	global latest_round
	ret = []
	response = requests.post(urls[0], data=json.dumps(get_latest_round_payload), headers=headers).json()
	new_latest_round = response["result"]
	for r in range(max(latest_round, new_latest_round-3)+1, new_latest_round+1):
		payload = {
				"method": "forensic_get_quorum_cert_at_round",
				"params": [r],
				"jsonrpc": "2.0",
				"id": 0,
				}
		hashes = []
		for url in urls:
			response = requests.post(url, data=json.dumps(payload), headers=headers).json()
			if len(response["result"])==0:
				hashes.append("err")
				continue
			is_nil = response["result"][0]["is_nil"]
			qc = response["result"][0]["qc"]
			# check round number
			if qc["vote_data"]["proposed"]["round"] == r:
				if is_nil:
					hashes.append("NIL BLOCK")
				else:
					hashes.append("'"+qc["vote_data"]["proposed"]["id"][:6]+"'")
			else:
				hashes.append("err")
		insert_qcs((r, hashes[0], hashes[1], hashes[2], hashes[3]))
		ret.append({"round":r, "node0": hashes[0], "node1": hashes[1], "node2": hashes[2], "node3": hashes[3]})
	latest_round = new_latest_round
	if r>2 and len(ret)>2:
		for node in nodes:
			insert_node(node, (ret[0]["round"], "{}:<br>{}".format(r-2, ret[0][node]), "{}:<br>{}".format(ret[1]["round"],ret[1][node]), "{}:<br>{}".format(ret[2]["round"],ret[2][node])))
	return ret
def get_logs():
	global nodes
	global log_files
	bufsize = 512
	for i, node in enumerate(nodes):
		fsize = os.stat(log_files[i]).st_size
		with open(log_files[i]) as stream:
			stream.seek(max(0,fsize-bufsize))
			the_log = stream.read()
			the_log = the_log[-bufsize:]
			sql_update = "UPDATE text SET content='{}' WHERE id='{}'".format(the_log, node)
			mycursor.execute(sql_update)
	mydb.commit()

def update(n):
	print("update", n)
	if n > 0:
		delete_qcs(3)
		for node in nodes:
			delete_node(node, 1)
	get_qcs_from_rpc(urls)
	get_logs()

if __name__ == "__main__":
	log_files = get_log_files()
	urls = get_urls()
	clear_images(1)
	clear_text(nodes)
	clear_qcs()
	clear_conflict()
	clear_culprits()
	for node in nodes:
		clear_node(node)
	clear_node("twin0")
	cnt = 0
	while True:
		update(cnt)
		time.sleep(5)
		cnt += 1
