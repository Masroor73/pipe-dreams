# Pipe Dreams — Data Sources

This file records dataset provenance, purpose, and limitations.

## 1. Case 8 Seed

Purpose:
- Case 8 starting point;
- organizer baseline / lab consequence comparability.

Known limitation:
- consequence is a hackathon lab label, not an official City consequence-of-failure score.

## 2. Open Calgary — Water Main Breaks

Purpose:
- historical break events;
- model training;
- rolling backtests;
- outcome evaluation.

Fields used depend on the exact downloaded export and must be documented in code/data report.

## 3. Open Calgary — Public Water Main

Purpose:
- pipe geometry;
- install year;
- material;
- diameter;
- length;
- pressure zone/current status where available.

Major limitation:
- present-day snapshot is not a complete historical asset registry.

Do not infer historical status from current `RETIRED` / `INACTIVE` without dated evidence.

## 4. Open Calgary — Community Boundaries

Provider:
- The City of Calgary.

Dataset:
- Community Boundaries.
- Open Calgary dataset ID: `ab7m-fwn6`.
- Permalink: `https://data.calgary.ca/d/ab7m-fwn6`
- Retrieved: 2026-10-03.
- Source CRS: EPSG:4326 (WGS84).
- Local downloaded file: `data/external/community_boundaries.csv`.
- Rows in downloaded snapshot: 313.

Purpose:
- community polygon geometry for community-level infrastructure analysis;
- clipping eligible water-main geometry to community boundaries;
- uniquely assigning historical and future break events to communities;
- generating frozen community GeoJSON map artifacts.

Fields used:
- `COMM_CODE` -> stable `community_id`;
- `NAME` -> `community_name`;
- `CLASS` -> contextual community classification;
- `SECTOR` -> contextual sector;
- `SRG` -> contextual growth/structure grouping;
- `MULTIPOLYGON` -> community boundary geometry.

Fields present but not currently used as model features:
- `CLASS_CODE`;
- `COMM_STRUCTURE`;
- `CREATED_DT`;
- `MODIFIED_DT`.

Processing:
- `MULTIPOLYGON` WKT is parsed into polygon geometry;
- geometries are projected to EPSG:3776 for spatial calculations;
- published GeoJSON artifacts are reprojected to EPSG:4326;
- community IDs are checked for missing and duplicate values before use.

Major limitations:
- the dataset is a present-day community-boundary snapshot, not a historical
  reconstruction of community boundaries at each validation cutoff;
- boundaries may have changed during the historical break record;
- a break on a shared boundary or matching multiple polygons is not silently
  assigned to a community;
- community geography does not imply hydraulic or water-network connectivity.

Attribution:
- Community boundary data provided by The City of Calgary through Open Calgary.

## 5. Provenance Requirements

Before submission record:
- source URL;
- download timestamp;
- file checksum;
- row count;
- snapshot date if known;
- fields used;
- exclusions.

## 6. Bearspaw Caution

Do not use an unverified asset match to claim:
- model rank;
- prediction;
- prevention.

A previous draft contained an incorrect/unverified statement about maximum diameter. Do not repeat it. Recompute any dataset statistic from the exact final input file before using it publicly.
