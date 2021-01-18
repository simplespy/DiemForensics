# Diem Forensics

---

## Summary

This project implements a forensic protocol that can irrefutably detect Byzantine parties in the rare case that there is a safety violation in Diem.

LibraBFT allows the Diem Blockchain to tolerate up to one-third Byzantine validators within the validator network under the partially synchronous network setting [1]. Let $n$ be the total number of validators in the Diem blockchain. In the rare case that the number of Byzantine validators $f$ exceeds $t=\frac{n}{3}$, security and liveness could be violated. This DIP focuses on the "forensic support" for safety violations: how to identify as many of the Byzantine validators by as many honest witnesses in as distributed manner as possible. We demonstrate a concrete protocol that when $f$ exceeds $t$, at least $t+1$ of culpable validators can be identified (with cryptographic integrity) by at least $2t+1−f$ honest validators individually.


## Motivation
An important property satisfied by any Byzantine fault tolerant consensus protocol is *agreement*, which requires honest parties to not decide on conflicting values. Depending on the network model, typical consensus protocols tolerate only a fraction of Byzantine parties. In particular, LibraBFT can tolerate $t=\frac{n}{3}$ Byzantine validators. If the number of Byzantine validators exceeds this threshold, the protocols do not provide safety (or liveness).

Motivated by situations where $\ge\frac{n}{3}$ Byzantine validators have successfully mounted a safety attack, this DIP focuses on providing forensic support to identify the validators that acted maliciously. Specifically, we demonstrate that *strong forensic support* can be provided for LibraBFT as presently implemented (no changes necessary):  there exist $2t+1-f$  honest validators who can individually identify at least $t+1$ Byzantine validators and provide irrefutable evidence to an external client.

## Safety Violation on Diem

### BFT assumption

The safety of Diem is based on a key assumption:  if there are $f$ Byzantine validators, there exist $2f + 1$ honest validators; so $f < \frac{n}{3}$. Mathematically, the following two lemmas underpin the safety guarantee.

1. There can only be one certified block per round.
2. Two blocks committed in different rounds must belong to the same chain.

Informally, the first lemma holds because Diem ensures that an honest validator only votes once in a round. Therefore, when the adversary does not corrupt more than $t$ validators, there cannot be two conflicting quorum certificates (QCs) within a round, since two conflicting QCs indicate $t+1$ validators vote for two conflicting blocks, which means $t+1$ validators are corrupted.

For the second argument, when the adversary does not corrupt more than $t$ validators, Diem ensures safety across rounds by a simple voting rule. Whenever validators receive a block, they maintain a preferred round, defined as the highest known grandparent round (also called a lock). The rule is that validators vote for a block if its parent round is at least the preferred round [[1]](https://developers.diem.com/docs/technical-papers/state-machine-validatortion-paper/). If a QC commits block $B$ in round $e+2$ (the QC is called commitQC for block $B$), at least $2t+1$ validators remember $e$ as their preferred rounds. In rounds higher than $e$, there could not be a QC on blocks that are not descendants of $B$, since such a quorum certificate means $t+1$ validators (among $2t+1$ validators) who lock on $(B,e)$ vote for block $B'$ on a conflicting chain as $B$.

### Safety violation
When the assumption does not hold, there are *exactly* two possible types of safety violations  (Figure 1).

1. Safety violation within a round: two different blocks are committed in a round
2. Safety violation across rounds: two blocks that belong to two conflicting chains are committed in different rounds.

<figure class="image">
  <img src="https://github.com/simplespy/dip/blob/master/dips/figure/safety_violation.png?raw=true" width="100%">
  <figcaption><center>Figure 1. Two types of safety violations. </center></figcaption>
</figure>


For the first case, when the adversary corrupts $\geq t+1$ validators, they can vote for two conflicting blocks, $B$ and $B'$ in the same round. Let us split $2t$ honest validators into two sets $P$ and $Q$. If the leader is corrupted, it can equivocate to validators in $P$ and $Q$. As a result, validators in $P$ vote for $B$ and validators in $Q$ vote for $B'$. Two conflicting blocks thus both get $2t+1$ votes, which are enough to form two conflicting QCs.

For the second case, when the adversary corrupts $\geq t+1$ validators, these validators can vote for a conflicting block $B'$ despite having a preferred round $e$ on block $B$. Again, let us split $2t$ honest validators into two sets $P$ and $Q$. Validators in $P$ vote for block $B$ in round $e+2$ and also lock on it whereas validators in $Q$ are not aware of block $B$ or the corresponding lock. Then in some higher round, a leader may propose a conflicting block $B'$ with an outdated QC. Validators in $Q$ are not aware of the lock on $B$ so they can vote for $B'$ along with the $t+1$ corrupted validators who violate the voting rule. As a result, the leader can collect $2t+1$ votes to form a QC in the higher round (also called a prepareQC). This QC is sufficient to unlock any honest validator and subsequently validators can commit a conflicting block.


## Forensic Support for Diem
---

In the  analysis of safety violation above, we observe that the corrupted validators must send certain messages in order to break safety: 1) to break safety within a round, corrupted validators vote for two conflicting blocks in the round, 2) to break safety across rounds, they vote for a conflicting block despite having a lock on a conflicting block (thus violating the voting rule). Those messages are signed by their secret keys and  hence can serve as irrefutable evidence of their misbehavior. In addition, no honest validator will vote twice within a round or violate the voting rule, therefore we will only hold corrupted validators culpable.

Armed with this intuition, the forensic protocol for LibraBFT is the following:

1. To identify disagreement and trigger the forensic protocol, two conflicting commitQCs need to be provided to the forensic protocol as input.
2. If two commitQCs are within a round, the validators who vote for both commitQCs are corrupted validators.
3. If two commitQCs are across rounds, we denote by commitQC<sub>1</sub> the lower one and commitQC<sub>2</sub> the higher one. We query all validators for a prepareQC (denoted by prepareQC<sup>#</sup>) such that it is later than commit<sub>1</sub>, the block $B'$ it votes for conflicts with the block $B$ of commitQC<sub>1</sub>, and the parent of $B'$ is before $B$. The validators who vote for commitQC<sub>1</sub> and prepareQC<sup>#</sup> are corrupted validators.

There are $n=3t+1$ validators in the system. In both of the cases, the process of identifying culpable Byzantine validators involves performing appropriate quorum intersections: since two quorums of $2t+1$ validators intersect in $t+1$ validators, we are able to identify $\geq t+1$ Byzantine validators. Who are the witnesses? For conflicting commits within a round, the commitQCs themselves can prove culpability. For conflicting commits across rounds, honest validators having access to prepareQC<sup>#</sup> are witnesses. It turns out that the existence of commit<sub>2</sub> implies that $2t+1$ validators should have received prepareQC<sup>#</sup>, out of which $f$ of them are Byzantine. The remaining $2t+1-f$ validators can act as witnesses. This also implies that the forensic support holds only when $f < 2t+1$; when the number of Byzantine validators are higher, we may have no witnesses. 

An example attack is depicted in Figure 2, where conflicting commits across rounds occur; here $t+1$ red validators are corrupted. An honest validator commits $B$ in round $e$ on receiving commitQC<sub>1</sub>. The formation of commitQC<sub>1</sub> indicates blue validators are locked on $(B,e)$.  Some rounds later, a malicious leader proposes a conflicting block $B'$ and sends the proposal to another set of honest validators. According to the voting rule, green validators will vote and a higher prepareQC<sup>#</sup> for $B'$ is formed. After two rounds of voting, $B'$ is committed by another honest validator. In this example, red validators are held accountable since they vote for both commitQC<sub>1</sub> and prepareQC<sup>#</sup>. Blue and green validators have access to the evidence.


<figure class="image">
  <img src="https://github.com/simplespy/dip/blob/master/dips/figure/attack.png?raw=true" width="100%">
  <figcaption><center>Figure 2. An attack in action, where red validators are held culpable for sending stale prepareQC during view change, blue and green validators are witnesses. </center></figcaption>
</figure>


## Specification
---

The forensic module can be added on top of Diem without touching the existing codebase. It consists of two components, a database [`FORENSIC_STORE`](https://github.com/BFTForensics/DiemForensics/blob/master/consensus/src/forensic_storage.rs) used to store quorum certificates received by validators, which can be accessed by clients through JSON-RPC requests, and an independent [`DETECTOR`](https://github.com/BFTForensics/DiemForensics/blob/master/scripts/forensics/grafana/utils.py) run by clients to analyze the forensic information.

<figure class="image">
  <img src="https://github.com/simplespy/dip/blob/master/dips/figure/forensic_store.png?raw=true" width="100%">
  <figcaption><center>Figure 3. Forensic module on top of Diem architechture. </center></figcaption>
</figure>

A demo dashboard below shows the information collected by the forensic protocol and the analysis results.

<figure class="image">
  <img src="https://github.com/simplespy/dip/blob/master/dips/figure/demo.png?raw=true" width="100%">
  <figcaption><center>Figure 4. Dashboard to display forensic information. </center></figcaption>
</figure>


## Compatibility
---

The forensic module does not conflict with existing versions of Diem. A Diem validator that supports forensics appears no different within the Diem payment network (DPN) to Diem validators running older software versions. Diem validators that support forensics can receive RPC requests from clients and reply with messages. Obviously, older validators are not capable of replying to forensic requests. If a client who wants to use forensic features has no peers that support forensics, then it cannot gather enough information to have forensic support thus naturally decays to older clients.


---
# References
---
1. State Machine Replication in the Diem Blockchain. [https://developers.diem.com/docs/technical-papers/state-machine-validatortion-paper/](https://developers.diem.com/docs/technical-papers/state-machine-validatortion-paper/)

