// Copyright (c) The Libra Core Contributors
// SPDX-License-Identifier: Apache-2.0

use anyhow::{ensure, Result};
use consensus_types::{
    quorum_cert::QuorumCert,
};
use libra_crypto::HashValue;
use libra_logger::prelude::*;
use libra_types::{
    block_info::Round,
};

use serde::{Deserialize, Serialize};
use schemadb::{ColumnFamilyName, ReadOptions, SchemaBatch, DB, DEFAULT_CF_NAME, define_schema, schema::{KeyCodec, ValueCodec}};
use std::{collections::HashMap, iter::Iterator, path::Path, time::Instant};
use crate::consensusdb::QCSchema;
use libra_infallible::RwLock;

const QC_CF_NAME: ColumnFamilyName = "quorum_certificate";
const ISNIL_CF_NAME: ColumnFamilyName = "is_nil";

#[derive(Debug, Eq, PartialEq)]
/// Struct storing `is nil block` bool
pub struct IsNil(bool);

impl IsNil {
    /// return bool is_nil
    pub fn is_nil(&self) -> bool {
        self.0
    }
}

#[derive(Deserialize, Serialize, Clone, Debug, Eq, PartialEq)]
/// Forensic QC: qc + is_nil. for convenient access to is_nil of a block and the qc for that block.
pub struct ForensicQuorumCert {
    /// the QC
    pub qc: QuorumCert,
    /// is_nil
    pub is_nil: bool,
}

impl ForensicQuorumCert {
    /// create a new data structure ForensicQuorumCert
    pub fn new(qc: QuorumCert, is_nil: bool) -> Self {
        Self {qc, is_nil}
    }
}

define_schema!(IsNilSchema, HashValue, IsNil, ISNIL_CF_NAME);

impl KeyCodec<IsNilSchema> for HashValue {
    fn encode_key(&self) -> Result<Vec<u8>> {
        Ok(self.to_vec())
    }

    fn decode_key(data: &[u8]) -> Result<Self> {
        Ok(HashValue::from_slice(data)?)
    }
}

impl ValueCodec<IsNilSchema> for IsNil {
    fn encode_value(&self) -> Result<Vec<u8>> {
        Ok(vec![self.0 as u8])
    }

    fn decode_value(data: &[u8]) -> Result<Self> {
        ensure!(data.len() == 1,"IsNil decoding failure");
        Ok(IsNil(data[0] != 0))
    }
}
/// Forensic Storage trait that serves as the storage of information necessary for forensics
pub trait ForensicStorage: Send + Sync {
    /// save a qc
    fn save_quorum_cert(&self, quorum_certs: &[QuorumCert]) -> Result<()>;
    /// get a vec of qc at a round
    fn get_quorum_cert_at_round(&self, round: Round) -> Result<Vec<ForensicQuorumCert>>;
    /// get the latest round known
    fn get_latest_round(&self) -> Result<Round>;
    /// Only save hash and is nil
    fn save_block(&self, hash: &HashValue, is_nil: bool) -> Result<()>;
}

/// Forensic DB, persistent database that implements forensic storage
pub struct ForensicDB {
    db: DB,
    round_to_qcs: RwLock<HashMap<Round,Vec<HashValue>>>,
    latest_round: RwLock<Round>,
}

impl ForensicDB {
    /// new forensic DB
    pub fn new<P: AsRef<Path> + Clone>(db_root_path: P) -> Self {
        let column_families = vec![
            /* UNUSED CF = */ DEFAULT_CF_NAME,
            QC_CF_NAME,
            ISNIL_CF_NAME,
        ];

        let path = db_root_path.as_ref().join("forensicdb");
        let instant = Instant::now();
        let db = DB::open(path.clone(), "forensic", column_families)
            .expect("ForensicDB open failed; unable to continue");
        let mut round_to_qcs: HashMap<Round,Vec<HashValue>> = HashMap::new();
        {
            let mut iter = db.iter::<QCSchema>(ReadOptions::default()).expect("ForensicDB iteration failed");
            iter.seek_to_first();
            let hashmap: HashMap<HashValue, QuorumCert> = iter.collect::<Result<HashMap<HashValue, QuorumCert>>>().expect("ForensicDB iteration failed");
            for qc in hashmap.values() {
                let round = qc.vote_data().proposed().round();
                round_to_qcs.entry(round).or_default().push(qc.vote_data().proposed().id());
            }
        }

        info!(
            "Opened ForensicDB at {:?} in {} ms",
            path,
            instant.elapsed().as_millis()
        );

        let round_to_qcs = RwLock::new(round_to_qcs);
        let latest_round = RwLock::new(0);
        Self { db, round_to_qcs, latest_round }
    }

    /// Get qc given hash
    fn get_quorum_cert(&self, hash: &HashValue) -> Result<Option<QuorumCert>> {
        self.db.get::<QCSchema>(hash)
    }

    /// Get is_nil given hash
    fn get_is_nil(&self, hash: &HashValue) -> Result<Option<IsNil>> {
        self.db.get::<IsNilSchema>(hash)
    }
}

impl ForensicStorage for ForensicDB {

    fn save_quorum_cert(
        &self,
        qc_data: &[QuorumCert],
    ) -> Result<()> {
        if qc_data.is_empty() {
            //return Err(anyhow::anyhow!("qc data is empty!").into());
            return Ok(());
        }
        let mut batch = SchemaBatch::new();
        qc_data
            .iter()
            .map(|qc| batch.put::<QCSchema>(&qc.vote_data().proposed().id(), qc))
            .collect::<Result<()>>()?;
        self.db.write_schemas(batch)?;
        let mut round_to_qcs = self.round_to_qcs.write();
        qc_data.iter().for_each(|qc| {
            let mut latest_round = self.latest_round.write();
            let r = qc.vote_data().proposed().round();
            if r > *latest_round {
                *latest_round = r;
            }
            drop(latest_round);
            round_to_qcs.entry(r).or_default().push(qc.vote_data().proposed().id())
        }
        );
        Ok(())
    }

    fn get_quorum_cert_at_round(&self, round: u64) -> Result<Vec<ForensicQuorumCert>> {
        let round_to_qcs = self.round_to_qcs.read();
        if let Some(hashes) = round_to_qcs.get(&round) {
            let mut v = Vec::new();
            for h in hashes.iter() {
                let qc: Option<QuorumCert> = self.get_quorum_cert(h)?;
                let is_nil: Option<IsNil> = self.get_is_nil(h)?;
                ensure!(qc.is_some(), "No such QC, round: {}, hash {}.", round, h);
                ensure!(is_nil.is_some(), "No such IsNil, round: {}, hash {}.", round, h);
                v.push(ForensicQuorumCert::new(qc.unwrap(),is_nil.unwrap().is_nil()));
            }
            Ok(v)
        } else {
            Ok(Vec::new())
        }
    }

    fn get_latest_round(&self) -> Result<Round> {
        let latest_round = self.latest_round.read();
        Ok(*latest_round)
    }

    fn save_block(&self, hash: &HashValue, is_nil: bool) -> Result<()> {
        let mut batch = SchemaBatch::new();
        batch.put::<IsNilSchema>(hash, &IsNil(is_nil))?;
        self.db.write_schemas(batch)
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use consensus_types::block::block_test_utils::certificate_for_genesis;
    use libra_temppath::TempPath;

    #[test]
    fn test_put_get() {
        let tmp_dir = TempPath::new();
        let db = ForensicDB::new(&tmp_dir);

        let qcs = vec![certificate_for_genesis()];
        db.save_quorum_cert(&qcs).unwrap();
        db.save_block(&certificate_for_genesis().vote_data().proposed().id(),false).unwrap();

        assert_eq!(db.get_quorum_cert_at_round(0).unwrap().len(), 1);
        assert_eq!(db.get_latest_round().unwrap(), 0);
    }
}