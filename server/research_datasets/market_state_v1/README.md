# MARKET_STATE_V1 recovered canonical dataset

This directory materializes the existing canonical dataset
`MARKET_STATE_V1_436265d450475aaa` for read-only research use.

The two CSV files were recovered byte-for-byte from the historical working
copy at `server/research_scripts/phase5/data/`. They were not regenerated and
are not a V2 dataset. Their SHA-256 values match
`server/research_scripts/phase5_5/dataset_version_v1.json`.

The original Dukascopy tick-manifest file is not materialized in the current
repository. Its declared summary hash, the deterministic builder hashes, the
CSV hashes, and the byte-identical rebuild evidence remain available in the
referenced provenance artifacts. Consumers must verify `manifest.json` before
reading either CSV and must fail closed on any mismatch.

These data have already been exposed to prior research. Their validation
integrity classification is `DISCOVERY_REUSE`; they are not a true holdout.
