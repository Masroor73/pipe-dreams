import json
import tempfile
import unittest
from pathlib import Path

from pipe_dreams_engine.real_data import (
    ANALYSIS_CRS,
    load_breaks,
    load_communities,
    load_pipes,
    load_real_inputs,
)


class RealDataAdapterTests(
    unittest.TestCase
):
    def test_loads_breaks_into_standard_schema(self):
        rows = [
            {
                "break_date": "2015-06-01T00:00:00.000",
                "break_type": "G",
                "status": "ACTIVE",
                "point": {
                    "type": "Point",
                    "coordinates": [
                        -114.07,
                        51.04,
                    ],
                },
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "breaks.json"
            path.write_text(
                json.dumps(rows)
            )

            result = load_breaks(
                path
            )

            self.assertEqual(
                len(result),
                1,
            )

            self.assertEqual(
                result.loc[
                    0,
                    "break_year",
                ],
                2015,
            )

            self.assertEqual(
                result.crs.to_string(),
                ANALYSIS_CRS,
            )

            self.assertEqual(
                result.geometry.iloc[
                    0
                ].geom_type,
                "Point",
            )

    def test_loads_pipes_into_standard_schema(self):
        rows = [
            {
                "year": "2001",
                "globalid": "pipe-1",
                "length": "10.0",
                "material": "PVC",
                "diam": "200",
                "p_zone": "Z1",
                "status_ind": "ACTIVE",
                "multilinestring": {
                    "type": "MultiLineString",
                    "coordinates": [
                        [
                            [
                                -114.07,
                                51.04,
                            ],
                            [
                                -114.06,
                                51.04,
                            ],
                        ]
                    ],
                },
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pipes.json"
            path.write_text(
                json.dumps(rows)
            )

            result = load_pipes(
                path
            )

            self.assertEqual(
                result.loc[
                    0,
                    "install_year",
                ],
                2001,
            )

            self.assertEqual(
                result.loc[
                    0,
                    "asset_id",
                ],
                "pipe-1",
            )

            self.assertEqual(
                result.crs.to_string(),
                ANALYSIS_CRS,
            )

    def test_loads_community_wkt_into_standard_schema(self):
        csv_text = (
            "COMM_CODE,NAME,CLASS,SECTOR,SRG,MULTIPOLYGON\n"
            'C1,Example,Residential,North,1,'
            '"MULTIPOLYGON (((-114.08 51.03, '
            '-114.06 51.03, '
            '-114.06 51.05, '
            '-114.08 51.05, '
            '-114.08 51.03)))"\n'
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = (
                Path(tmp)
                / "communities.csv"
            )

            path.write_text(
                csv_text
            )

            result = load_communities(
                path
            )

            self.assertEqual(
                len(result),
                1,
            )

            self.assertEqual(
                result.loc[
                    0,
                    "community_id",
                ],
                "C1",
            )

            self.assertEqual(
                result.loc[
                    0,
                    "community_name",
                ],
                "Example",
            )

            self.assertEqual(
                result.crs.to_string(),
                ANALYSIS_CRS,
            )

    def test_real_input_diagnostics_are_reported(self):
        breaks_rows = [
            {
                "break_date": "2015-06-01T00:00:00.000",
                "break_type": "G",
                "status": "ACTIVE",
                "point": {
                    "type": "Point",
                    "coordinates": [
                        -114.07,
                        51.04,
                    ],
                },
            }
        ]

        pipe_rows = [
            {
                "year": "2033",
                "globalid": "planned-1",
                "length": "10",
                "material": "PVC",
                "diam": "200",
                "p_zone": "Z1",
                "status_ind": "PLANNED",
                "multilinestring": {
                    "type": "MultiLineString",
                    "coordinates": [
                        [
                            [
                                -114.07,
                                51.04,
                            ],
                            [
                                -114.06,
                                51.04,
                            ],
                        ]
                    ],
                },
            },
            {
                "year": "2001",
                "globalid": "active-1",
                "length": "10",
                "material": "PVC",
                "diam": "200",
                "p_zone": "Z1",
                "status_ind": "ACTIVE",
                "multilinestring": {
                    "type": "MultiLineString",
                    "coordinates": [
                        [
                            [
                                -114.07,
                                51.04,
                            ],
                            [
                                -114.06,
                                51.04,
                            ],
                        ]
                    ],
                },
            },
        ]

        community_csv = (
            "COMM_CODE,NAME,MULTIPOLYGON\n"
            'C1,Example,'
            '"MULTIPOLYGON (((-114.08 51.03, '
            '-114.06 51.03, '
            '-114.06 51.05, '
            '-114.08 51.05, '
            '-114.08 51.03)))"\n'
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            breaks_path = (
                root / "breaks.json"
            )
            pipes_path = (
                root / "pipes.json"
            )
            communities_path = (
                root / "communities.csv"
            )

            breaks_path.write_text(
                json.dumps(
                    breaks_rows
                )
            )

            pipes_path.write_text(
                json.dumps(
                    pipe_rows
                )
            )

            communities_path.write_text(
                community_csv
            )

            (
                communities,
                pipes,
                breaks,
                diagnostics,
            ) = load_real_inputs(
                breaks_path=breaks_path,
                pipes_path=pipes_path,
                communities_path=communities_path,
            )

            self.assertEqual(
                len(communities),
                1,
            )

            self.assertEqual(
                len(pipes),
                1,
            )

            self.assertEqual(
                pipes.loc[
                    0,
                    "asset_id",
                ],
                "active-1",
            )

            self.assertEqual(
                diagnostics[
                    "pipe_rows"
                ],
                2,
            )

            self.assertEqual(
                diagnostics[
                    "pipe_rows_eligible"
                ],
                1,
            )

            self.assertEqual(
                diagnostics[
                    "pipe_rows_excluded"
                ],
                1,
            )

            self.assertEqual(
                len(breaks),
                1,
            )

            self.assertEqual(
                diagnostics[
                    "pipe_future_after_2026"
                ],
                1,
            )

            self.assertEqual(
                diagnostics[
                    "pipe_planned_rows"
                ],
                1,
            )


if __name__ == "__main__":
    unittest.main()