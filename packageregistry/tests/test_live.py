"""Live integration tests for Package Registry API -- hits the real NPM and PyPI APIs.

Run with:
    PACKAGEREGISTRY_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) NPM and PyPI endpoints.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

pytestmark = pytest.mark.skipif(
    os.getenv("PACKAGEREGISTRY_RUN_LIVE_TESTS") != "1",
    reason="Set PACKAGEREGISTRY_RUN_LIVE_TESTS=1 to run live Package Registry API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from packageregistry_mcp.gen.packageregistry.v1 import packageregistry_pb2 as _pb  # noqa: F401
    from packageregistry_mcp.service import PackageRegistryService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-packageregistry-live", version="0.0.1"
    )
    servicer = PackageRegistryService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- Shared fixtures for data discovery ---


@pytest.fixture(scope="module")
def npm_package_version(live_server):
    """Discover a valid NPM package version for detail tests."""
    result = live_server._cli(
        [
            "PackageRegistryService",
            "GetNPMPackage",
            "-r",
            json.dumps({"name": "express"}),
        ]
    )
    version = result.get("latestVersion") or result.get("latest_version", "")
    assert version, "expected a latest version for express"
    return version


@pytest.fixture(scope="module")
def pypi_package_version(live_server):
    """Discover a valid PyPI package version for detail tests."""
    result = live_server._cli(
        [
            "PackageRegistryService",
            "GetPyPIPackage",
            "-r",
            json.dumps({"name": "requests"}),
        ]
    )
    version = result.get("version", "")
    assert version, "expected a version for requests"
    return version


# --- NPM: Search ---


class TestLiveNPMSearch:
    def test_search_npm(self, live_server):
        result = live_server._cli(
            [
                "PackageRegistryService",
                "SearchNPM",
                "-r",
                json.dumps({"query": "react", "size": 5}),
            ]
        )
        results = result.get("results", [])
        assert isinstance(results, list)
        assert len(results) > 0
        r = results[0]
        assert "name" in r
        assert "version" in r

    def test_search_npm_with_keyword(self, live_server):
        result = live_server._cli(
            [
                "PackageRegistryService",
                "SearchNPM",
                "-r",
                json.dumps({"query": "typescript", "size": 3}),
            ]
        )
        results = result.get("results", [])
        assert isinstance(results, list)
        assert len(results) > 0
        total = result.get("total", 0)
        assert int(total) > 0


# --- NPM: Package metadata ---


class TestLiveNPMPackage:
    def test_get_npm_package(self, live_server):
        result = live_server._cli(
            [
                "PackageRegistryService",
                "GetNPMPackage",
                "-r",
                json.dumps({"name": "express"}),
            ]
        )
        assert result.get("name") == "express"
        version = result.get("latestVersion") or result.get("latest_version", "")
        assert version
        desc = result.get("description", "")
        assert desc

    def test_get_npm_package_scoped(self, live_server):
        result = live_server._cli(
            [
                "PackageRegistryService",
                "GetNPMPackage",
                "-r",
                json.dumps({"name": "lodash"}),
            ]
        )
        assert result.get("name") == "lodash"
        version = result.get("latestVersion") or result.get("latest_version", "")
        assert version


# --- NPM: Downloads ---


class TestLiveNPMDownloads:
    def test_get_npm_downloads(self, live_server):
        result = live_server._cli(
            [
                "PackageRegistryService",
                "GetNPMDownloads",
                "-r",
                json.dumps({"name": "express"}),
            ]
        )
        downloads = result.get("downloads", 0)
        assert int(downloads) > 0
        start = result.get("startDate") or result.get("start_date", "")
        end = result.get("endDate") or result.get("end_date", "")
        assert start
        assert end


# --- NPM: Versions ---


class TestLiveNPMVersions:
    def test_get_npm_versions(self, live_server):
        result = live_server._cli(
            [
                "PackageRegistryService",
                "GetNPMVersions",
                "-r",
                json.dumps({"name": "express"}),
            ]
        )
        versions = result.get("versions", [])
        assert isinstance(versions, list)
        assert len(versions) > 0
        v = versions[0]
        assert "version" in v


# --- NPM: Dependencies ---


class TestLiveNPMDependencies:
    def test_get_npm_dependencies(self, live_server):
        result = live_server._cli(
            [
                "PackageRegistryService",
                "GetNPMDependencies",
                "-r",
                json.dumps({"name": "express"}),
            ]
        )
        deps = result.get("dependencies", [])
        assert isinstance(deps, list)
        assert len(deps) > 0
        d = deps[0]
        assert "name" in d
        spec = d.get("versionSpec") or d.get("version_spec", "")
        assert spec

    def test_get_npm_dependencies_with_version(self, live_server, npm_package_version):
        result = live_server._cli(
            [
                "PackageRegistryService",
                "GetNPMDependencies",
                "-r",
                json.dumps({"name": "express", "version": npm_package_version}),
            ]
        )
        deps = result.get("dependencies", [])
        assert isinstance(deps, list)
        assert len(deps) > 0


# --- PyPI: Package metadata ---


class TestLivePyPIPackage:
    def test_get_pypi_package(self, live_server):
        result = live_server._cli(
            [
                "PackageRegistryService",
                "GetPyPIPackage",
                "-r",
                json.dumps({"name": "requests"}),
            ]
        )
        assert result.get("name") == "requests"
        assert result.get("version")
        summary = result.get("summary", "")
        assert summary

    def test_get_pypi_package_flask(self, live_server):
        result = live_server._cli(
            [
                "PackageRegistryService",
                "GetPyPIPackage",
                "-r",
                json.dumps({"name": "flask"}),
            ]
        )
        # PyPI normalizes package names, so it might be "Flask" or "flask"
        name = result.get("name", "").lower()
        assert "flask" in name
        assert result.get("version")


# --- PyPI: Version ---


class TestLivePyPIVersion:
    def test_get_pypi_version(self, live_server, pypi_package_version):
        result = live_server._cli(
            [
                "PackageRegistryService",
                "GetPyPIVersion",
                "-r",
                json.dumps({"name": "requests", "version": pypi_package_version}),
            ]
        )
        assert result.get("version") == pypi_package_version
        assert result.get("name") == "requests"


# --- PyPI: Releases ---


class TestLivePyPIReleases:
    def test_get_pypi_releases(self, live_server):
        result = live_server._cli(
            [
                "PackageRegistryService",
                "GetPyPIReleases",
                "-r",
                json.dumps({"name": "requests"}),
            ]
        )
        releases = result.get("releases", [])
        assert isinstance(releases, list)
        assert len(releases) > 0
        r = releases[0]
        assert "version" in r


# --- PyPI: Downloads ---


class TestLivePyPIDownloads:
    def test_get_pypi_downloads(self, live_server):
        result = live_server._cli(
            [
                "PackageRegistryService",
                "GetPyPIDownloads",
                "-r",
                json.dumps({"name": "requests"}),
            ]
        )
        last_day = result.get("lastDay") or result.get("last_day", 0)
        last_week = result.get("lastWeek") or result.get("last_week", 0)
        last_month = result.get("lastMonth") or result.get("last_month", 0)
        assert int(last_day) > 0
        assert int(last_week) > 0
        assert int(last_month) > 0


# --- PyPI: Dependencies ---


class TestLivePyPIDependencies:
    def test_get_pypi_dependencies(self, live_server):
        result = live_server._cli(
            [
                "PackageRegistryService",
                "GetPyPIDependencies",
                "-r",
                json.dumps({"name": "requests"}),
            ]
        )
        requires = result.get("requiresDist") or result.get("requires_dist", [])
        assert isinstance(requires, list)
        assert len(requires) > 0

    def test_get_pypi_dependencies_with_version(self, live_server, pypi_package_version):
        result = live_server._cli(
            [
                "PackageRegistryService",
                "GetPyPIDependencies",
                "-r",
                json.dumps({"name": "requests", "version": pypi_package_version}),
            ]
        )
        requires = result.get("requiresDist") or result.get("requires_dist", [])
        assert isinstance(requires, list)
        assert len(requires) > 0
        python_req = result.get("requiresPython") or result.get("requires_python", "")
        assert python_req
