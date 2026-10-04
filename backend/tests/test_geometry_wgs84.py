from app.services.artifact_service import _geojson


def test_projected_engine_geometry_is_served_as_wgs84():
    geo = _geojson(
        "MULTILINESTRING ((-5303.433704490083 5655734.298080726, "
        "-5303.43295106427 5655735.03225058))"
    )
    lon, lat = geo["coordinates"][0][0]
    assert abs(lon - -114.0756) < 1e-3
    assert abs(lat - 51.0379) < 1e-3


def test_wgs84_geometry_is_unchanged():
    geo = _geojson("LINESTRING (-114.07 51.03, -114.06 51.04)")
    assert geo["coordinates"] == [[-114.07, 51.03], [-114.06, 51.04]]
