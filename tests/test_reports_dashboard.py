"""Test Dashboard metrics and Reports with CSV export."""
from app.models.hotel import Room
from app.models.restaurant import RestaurantTable


def test_dashboard_view(auth_client):
    dash_resp = auth_client.get('/')
    assert dash_resp.status_code == 200
    assert b"Operations Overview" in dash_resp.data
    assert b"Hotel Rooms" in dash_resp.data


def test_reports_view_and_csv_export(admin_client):
    # Occupancy report
    rep_resp = admin_client.get('/reports/?report_type=occupancy')
    assert rep_resp.status_code == 200
    assert b"Occupancy Breakdown" in rep_resp.data

    # Revenue report
    rev_resp = admin_client.get('/reports/?report_type=revenue')
    assert rev_resp.status_code == 200

    # CSV Export
    csv_resp = admin_client.get('/reports/export-csv?report_type=revenue')
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["Content-Type"]
