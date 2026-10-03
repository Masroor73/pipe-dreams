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

## 4. Provenance Requirements

Before submission record:
- source URL;
- download timestamp;
- file checksum;
- row count;
- snapshot date if known;
- fields used;
- exclusions.

## 5. Bearspaw Caution

Do not use an unverified asset match to claim:
- model rank;
- prediction;
- prevention.

A previous draft contained an incorrect/unverified statement about maximum diameter. Do not repeat it. Recompute any dataset statistic from the exact final input file before using it publicly.
