"""Unit tests -- every SpaceXService RPC method, mocked HTTP."""

import pytest

from spacex_mcp.gen.spacex.v1 import spacex_pb2 as pb
from tests.conftest import (
    FAKE_COMPANY,
    FAKE_CREW_MEMBER,
    FAKE_LAUNCH,
    FAKE_LAUNCH_UPCOMING,
    FAKE_LAUNCHPAD,
    FAKE_ROCKET,
    FAKE_STARLINK,
)


class TestGetLatestLaunch:
    def test_returns_launch(self, service):
        resp = service.GetLatestLaunch(pb.GetLatestLaunchRequest())
        assert resp.launch.id == FAKE_LAUNCH["id"]
        assert resp.launch.name == FAKE_LAUNCH["name"]

    def test_launch_fields(self, service):
        resp = service.GetLatestLaunch(pb.GetLatestLaunchRequest())
        l = resp.launch
        assert l.date_utc == FAKE_LAUNCH["date_utc"]
        assert l.date_unix == FAKE_LAUNCH["date_unix"]
        assert l.success is True
        assert l.flight_number == 250
        assert l.rocket == FAKE_LAUNCH["rocket"]
        assert l.details == FAKE_LAUNCH["details"]
        assert l.upcoming is False

    def test_launch_links(self, service):
        resp = service.GetLatestLaunch(pb.GetLatestLaunchRequest())
        l = resp.launch
        assert l.patch_small == FAKE_LAUNCH["links"]["patch"]["small"]
        assert l.patch_large == FAKE_LAUNCH["links"]["patch"]["large"]
        assert l.webcast == FAKE_LAUNCH["links"]["webcast"]
        assert l.wikipedia == FAKE_LAUNCH["links"]["wikipedia"]
        assert l.article == FAKE_LAUNCH["links"]["article"]

    def test_launch_payloads(self, service):
        resp = service.GetLatestLaunch(pb.GetLatestLaunchRequest())
        assert list(resp.launch.payloads) == FAKE_LAUNCH["payloads"]


class TestGetLaunches:
    def test_returns_all_launches(self, service):
        resp = service.GetLaunches(pb.GetLaunchesRequest())
        assert len(resp.launches) == 2

    def test_includes_past_and_upcoming(self, service):
        resp = service.GetLaunches(pb.GetLaunchesRequest())
        ids = {l.id for l in resp.launches}
        assert FAKE_LAUNCH["id"] in ids
        assert FAKE_LAUNCH_UPCOMING["id"] in ids

    def test_upcoming_flag(self, service):
        resp = service.GetLaunches(pb.GetLaunchesRequest())
        upcoming = [l for l in resp.launches if l.upcoming]
        assert len(upcoming) == 1
        assert upcoming[0].id == FAKE_LAUNCH_UPCOMING["id"]


class TestGetLaunch:
    def test_returns_specific_launch(self, service):
        resp = service.GetLaunch(
            pb.GetLaunchRequest(id="5eb87d46ffd86e000604b388")
        )
        assert resp.launch.id == FAKE_LAUNCH["id"]
        assert resp.launch.name == FAKE_LAUNCH["name"]

    def test_calls_correct_endpoint(self, service, mock_http):
        service.GetLaunch(pb.GetLaunchRequest(id="5eb87d46ffd86e000604b388"))
        call_url = mock_http.get.call_args[0][0]
        assert "/v4/launches/5eb87d46ffd86e000604b388" in call_url


class TestGetRockets:
    def test_returns_rockets(self, service):
        resp = service.GetRockets(pb.GetRocketsRequest())
        assert len(resp.rockets) == 1
        r = resp.rockets[0]
        assert r.id == FAKE_ROCKET["id"]
        assert r.name == "Falcon 9"

    def test_rocket_specs(self, service):
        resp = service.GetRockets(pb.GetRocketsRequest())
        r = resp.rockets[0]
        assert r.active is True
        assert r.stages == 2
        assert r.cost_per_launch == 50000000
        assert r.first_flight == "2010-06-04"
        assert r.country == "United States"
        assert r.company == "SpaceX"

    def test_rocket_dimensions(self, service):
        resp = service.GetRockets(pb.GetRocketsRequest())
        r = resp.rockets[0]
        assert r.height_meters == 70.0
        assert r.diameter_meters == 3.7
        assert r.mass_kg == 549054.0

    def test_rocket_payload_capacity(self, service):
        resp = service.GetRockets(pb.GetRocketsRequest())
        r = resp.rockets[0]
        assert r.payload_weight_leo_kg == 22800.0
        assert r.payload_weight_gto_kg == 8300.0

    def test_rocket_engines(self, service):
        resp = service.GetRockets(pb.GetRocketsRequest())
        r = resp.rockets[0]
        assert r.engines_number == 9
        assert r.engine_type == "merlin"
        assert r.engine_propellant_1 == "liquid oxygen"
        assert r.engine_propellant_2 == "RP-1 kerosene"

    def test_rocket_metadata(self, service):
        resp = service.GetRockets(pb.GetRocketsRequest())
        r = resp.rockets[0]
        assert "two-stage rocket" in r.description
        assert r.wikipedia == FAKE_ROCKET["wikipedia"]
        assert r.success_rate_pct == 98


class TestGetRocket:
    def test_returns_specific_rocket(self, service):
        resp = service.GetRocket(
            pb.GetRocketRequest(id="5e9d0d95eda69973a809d1ec")
        )
        assert resp.rocket.name == "Falcon 9"

    def test_calls_correct_endpoint(self, service, mock_http):
        service.GetRocket(pb.GetRocketRequest(id="5e9d0d95eda69973a809d1ec"))
        call_url = mock_http.get.call_args[0][0]
        assert "/v4/rockets/5e9d0d95eda69973a809d1ec" in call_url


class TestGetCrew:
    def test_returns_crew(self, service):
        resp = service.GetCrew(pb.GetCrewRequest())
        assert len(resp.crew) == 1

    def test_crew_fields(self, service):
        resp = service.GetCrew(pb.GetCrewRequest())
        c = resp.crew[0]
        assert c.id == FAKE_CREW_MEMBER["id"]
        assert c.name == "Robert Behnken"
        assert c.status == "active"
        assert c.agency == "NASA"
        assert c.image == FAKE_CREW_MEMBER["image"]
        assert c.wikipedia == FAKE_CREW_MEMBER["wikipedia"]
        assert list(c.launches) == FAKE_CREW_MEMBER["launches"]


class TestGetStarlink:
    def test_returns_satellites(self, service):
        resp = service.GetStarlink(pb.GetStarlinkRequest())
        assert len(resp.satellites) == 1

    def test_satellite_fields(self, service):
        resp = service.GetStarlink(pb.GetStarlinkRequest())
        s = resp.satellites[0]
        assert s.id == FAKE_STARLINK["id"]
        assert s.version == "v1.0"
        assert s.launch == FAKE_STARLINK["launch"]
        assert s.height_km == 550.5
        assert s.latitude == 45.123
        assert s.longitude == -93.456
        assert s.velocity_kms == 7.6


class TestGetLaunchpads:
    def test_returns_launchpads(self, service):
        resp = service.GetLaunchpads(pb.GetLaunchpadsRequest())
        assert len(resp.launchpads) == 1

    def test_launchpad_fields(self, service):
        resp = service.GetLaunchpads(pb.GetLaunchpadsRequest())
        lp = resp.launchpads[0]
        assert lp.id == FAKE_LAUNCHPAD["id"]
        assert lp.name == "KSC LC 39A"
        assert lp.full_name == "Kennedy Space Center Historic Launch Complex 39A"
        assert lp.locality == "Cape Canaveral"
        assert lp.region == "Florida"
        assert lp.latitude == 28.6080585
        assert lp.longitude == -80.6039558
        assert lp.launch_attempts == 200
        assert lp.launch_successes == 198
        assert lp.status == "active"


class TestGetCompanyInfo:
    def test_basic_info(self, service):
        resp = service.GetCompanyInfo(pb.GetCompanyInfoRequest())
        assert resp.name == "SpaceX"
        assert resp.founder == "Elon Musk"
        assert resp.founded == 2002
        assert resp.employees == 12000

    def test_leadership(self, service):
        resp = service.GetCompanyInfo(pb.GetCompanyInfoRequest())
        assert resp.ceo == "Elon Musk"
        assert resp.cto == "Elon Musk"
        assert resp.coo == "Gwynne Shotwell"
        assert resp.cto_propulsion == "Tom Mueller"

    def test_company_metrics(self, service):
        resp = service.GetCompanyInfo(pb.GetCompanyInfoRequest())
        assert resp.vehicles == 4
        assert resp.launch_sites == 3
        assert resp.test_sites == 3
        assert resp.valuation == 74000000000

    def test_headquarters(self, service):
        resp = service.GetCompanyInfo(pb.GetCompanyInfoRequest())
        assert resp.headquarters_city == "Hawthorne"
        assert resp.headquarters_state == "California"

    def test_links(self, service):
        resp = service.GetCompanyInfo(pb.GetCompanyInfoRequest())
        assert resp.website == "https://www.spacex.com"
        assert resp.flickr == "https://www.flickr.com/photos/spacex/"
        assert resp.twitter == "https://twitter.com/SpaceX"
        assert resp.elon_twitter == "https://twitter.com/elonmusk"

    def test_summary(self, service):
        resp = service.GetCompanyInfo(pb.GetCompanyInfoRequest())
        assert "SpaceX" in resp.summary


class TestGetUpcomingLaunches:
    def test_returns_upcoming(self, service):
        resp = service.GetUpcomingLaunches(pb.GetUpcomingLaunchesRequest())
        assert len(resp.launches) == 1
        assert resp.launches[0].upcoming is True
        assert resp.launches[0].id == FAKE_LAUNCH_UPCOMING["id"]

    def test_upcoming_launch_name(self, service):
        resp = service.GetUpcomingLaunches(pb.GetUpcomingLaunchesRequest())
        assert resp.launches[0].name == "Starlink Group 10-1"

    def test_null_fields_handled(self, service):
        resp = service.GetUpcomingLaunches(pb.GetUpcomingLaunchesRequest())
        l = resp.launches[0]
        # success is None in the API, should be False (proto default)
        assert l.success is False
        # details is None, should be empty string
        assert l.details == ""
        # patch URLs are None, should be empty strings
        assert l.patch_small == ""
        assert l.patch_large == ""
