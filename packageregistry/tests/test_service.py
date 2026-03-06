"""Unit tests — every PackageRegistryService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from packageregistry_mcp.gen.packageregistry.v1 import packageregistry_pb2 as pb
from tests.conftest import (
    FAKE_NPM_SEARCH,
    FAKE_NPM_PACKAGE,
    FAKE_NPM_DOWNLOADS,
    FAKE_PYPI_PACKAGE,
    FAKE_PYPI_VERSION,
    FAKE_PYPI_DOWNLOADS,
)


class TestSearchNPM:
    def test_returns_results(self, service):
        resp = service.SearchNPM(pb.SearchNPMRequest(query="react"))
        assert len(resp.results) == 2
        assert resp.total == 2

    def test_first_result_fields(self, service):
        resp = service.SearchNPM(pb.SearchNPMRequest(query="react"))
        r = resp.results[0]
        assert r.name == "react"
        assert r.version == "18.2.0"
        assert r.description == "A JavaScript library for building user interfaces"
        assert "react" in r.keywords
        assert r.publisher == "gaearon"
        assert r.homepage == "https://react.dev"
        assert r.repository == "https://github.com/facebook/react"

    def test_default_size(self, service, mock_http):
        service.SearchNPM(pb.SearchNPMRequest(query="react"))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("size") == 20

    def test_custom_size(self, service, mock_http):
        service.SearchNPM(pb.SearchNPMRequest(query="react", size=5))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("size") == 5

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={"total": 0, "objects": []})
        )
        resp = service.SearchNPM(pb.SearchNPMRequest(query="nonexistent"))
        assert len(resp.results) == 0
        assert resp.total == 0


class TestGetNPMPackage:
    def test_basic_fields(self, service):
        resp = service.GetNPMPackage(pb.GetNPMPackageRequest(name="express"))
        assert resp.name == "express"
        assert resp.latest_version == "4.18.2"
        assert resp.description == "Fast, unopinionated, minimalist web framework"
        assert resp.license == "MIT"

    def test_homepage_and_repo(self, service):
        resp = service.GetNPMPackage(pb.GetNPMPackageRequest(name="express"))
        assert resp.homepage == "http://expressjs.com/"
        assert resp.repository_url == "https://github.com/expressjs/express.git"

    def test_maintainers(self, service):
        resp = service.GetNPMPackage(pb.GetNPMPackageRequest(name="express"))
        assert len(resp.maintainers) == 2
        assert resp.maintainers[0].name == "dougwilson"
        assert resp.maintainers[0].email == "doug@somethingdoug.com"

    def test_dist_tags(self, service):
        resp = service.GetNPMPackage(pb.GetNPMPackageRequest(name="express"))
        assert resp.dist_tags["latest"] == "4.18.2"
        assert resp.dist_tags["next"] == "5.0.0-beta.1"

    def test_timestamps(self, service):
        resp = service.GetNPMPackage(pb.GetNPMPackageRequest(name="express"))
        assert resp.created == "2010-12-29T19:38:25.450Z"
        assert resp.last_modified == "2024-01-15T10:00:00.000Z"


class TestGetNPMDownloads:
    def test_returns_downloads(self, service):
        resp = service.GetNPMDownloads(pb.GetNPMDownloadsRequest(name="express"))
        assert resp.package_name == "express"
        assert resp.downloads == 25000000
        assert resp.start_date == "2025-01-08"
        assert resp.end_date == "2025-01-14"


class TestGetNPMVersions:
    def test_returns_versions(self, service):
        resp = service.GetNPMVersions(pb.GetNPMVersionsRequest(name="express"))
        assert resp.package_name == "express"
        assert len(resp.versions) == 2
        version_strs = {v.version for v in resp.versions}
        assert "4.18.1" in version_strs
        assert "4.18.2" in version_strs

    def test_version_dates(self, service):
        resp = service.GetNPMVersions(pb.GetNPMVersionsRequest(name="express"))
        v_map = {v.version: v.date for v in resp.versions}
        assert v_map["4.18.2"] == "2022-10-08T14:00:00.000Z"
        assert v_map["4.18.1"] == "2022-04-29T14:00:00.000Z"


class TestGetNPMDependencies:
    def test_returns_dependencies(self, service):
        resp = service.GetNPMDependencies(pb.GetNPMDependenciesRequest(name="express"))
        assert resp.package_name == "express"
        assert resp.version == "4.18.2"
        dep_names = {d.name for d in resp.dependencies}
        assert "accepts" in dep_names
        assert "body-parser" in dep_names

    def test_dev_dependencies(self, service):
        resp = service.GetNPMDependencies(pb.GetNPMDependenciesRequest(name="express"))
        dev_dep_names = {d.name for d in resp.dev_dependencies}
        assert "mocha" in dev_dep_names
        assert "supertest" in dev_dep_names

    def test_specific_version(self, service):
        resp = service.GetNPMDependencies(pb.GetNPMDependenciesRequest(name="express", version="4.18.1"))
        assert resp.version == "4.18.1"
        dep_map = {d.name: d.version_spec for d in resp.dependencies}
        assert dep_map["body-parser"] == "1.20.0"

    def test_dependency_version_specs(self, service):
        resp = service.GetNPMDependencies(pb.GetNPMDependenciesRequest(name="express"))
        dep_map = {d.name: d.version_spec for d in resp.dependencies}
        assert dep_map["accepts"] == "~1.3.8"
        assert dep_map["body-parser"] == "1.20.1"


class TestGetPyPIPackage:
    def test_basic_fields(self, service):
        resp = service.GetPyPIPackage(pb.GetPyPIPackageRequest(name="requests"))
        assert resp.name == "requests"
        assert resp.version == "2.31.0"
        assert resp.summary == "Python HTTP for Humans."
        assert resp.author == "Kenneth Reitz"
        assert resp.license == "Apache-2.0"

    def test_urls(self, service):
        resp = service.GetPyPIPackage(pb.GetPyPIPackageRequest(name="requests"))
        assert resp.home_page == "https://requests.readthedocs.io"
        url_map = {u.label: u.url for u in resp.project_urls}
        assert url_map["Documentation"] == "https://requests.readthedocs.io"
        assert url_map["Source"] == "https://github.com/psf/requests"

    def test_python_requirement(self, service):
        resp = service.GetPyPIPackage(pb.GetPyPIPackageRequest(name="requests"))
        assert resp.requires_python == ">=3.7"

    def test_classifiers(self, service):
        resp = service.GetPyPIPackage(pb.GetPyPIPackageRequest(name="requests"))
        assert len(resp.classifiers) == 4
        assert any("Production/Stable" in c for c in resp.classifiers)

    def test_description(self, service):
        resp = service.GetPyPIPackage(pb.GetPyPIPackageRequest(name="requests"))
        assert "Requests" in resp.description


class TestGetPyPIVersion:
    def test_returns_version_info(self, service):
        resp = service.GetPyPIVersion(pb.GetPyPIVersionRequest(name="requests", version="2.30.0"))
        assert resp.name == "requests"
        assert resp.version == "2.30.0"
        assert resp.summary == "Python HTTP for Humans."
        assert resp.author == "Kenneth Reitz"

    def test_upload_date(self, service):
        resp = service.GetPyPIVersion(pb.GetPyPIVersionRequest(name="requests", version="2.30.0"))
        assert resp.upload_date == "2023-05-22T15:00:00"

    def test_requires_dist(self, service):
        resp = service.GetPyPIVersion(pb.GetPyPIVersionRequest(name="requests", version="2.30.0"))
        assert len(resp.requires_dist) == 4
        assert any("charset-normalizer" in d for d in resp.requires_dist)

    def test_requires_python(self, service):
        resp = service.GetPyPIVersion(pb.GetPyPIVersionRequest(name="requests", version="2.30.0"))
        assert resp.requires_python == ">=3.7"


class TestGetPyPIReleases:
    def test_returns_releases(self, service):
        resp = service.GetPyPIReleases(pb.GetPyPIReleasesRequest(name="requests"))
        assert resp.package_name == "requests"
        assert len(resp.releases) == 2
        versions = {r.version for r in resp.releases}
        assert "2.30.0" in versions
        assert "2.31.0" in versions

    def test_release_dates(self, service):
        resp = service.GetPyPIReleases(pb.GetPyPIReleasesRequest(name="requests"))
        date_map = {r.version: r.upload_date for r in resp.releases}
        assert date_map["2.30.0"] == "2023-05-22T15:00:00"
        assert date_map["2.31.0"] == "2023-05-22T16:00:00"


class TestGetPyPIDownloads:
    def test_returns_download_stats(self, service):
        resp = service.GetPyPIDownloads(pb.GetPyPIDownloadsRequest(name="requests"))
        assert resp.package_name == "requests"
        assert resp.last_day == 5000000
        assert resp.last_week == 35000000
        assert resp.last_month == 150000000


class TestGetPyPIDependencies:
    def test_returns_dependencies(self, service):
        resp = service.GetPyPIDependencies(pb.GetPyPIDependenciesRequest(name="requests"))
        assert resp.package_name == "requests"
        assert resp.version == "2.31.0"
        assert len(resp.requires_dist) == 4
        assert any("urllib3" in d for d in resp.requires_dist)
        assert any("certifi" in d for d in resp.requires_dist)

    def test_requires_python(self, service):
        resp = service.GetPyPIDependencies(pb.GetPyPIDependenciesRequest(name="requests"))
        assert resp.requires_python == ">=3.7"

    def test_specific_version(self, service):
        resp = service.GetPyPIDependencies(pb.GetPyPIDependenciesRequest(name="requests", version="2.30.0"))
        assert resp.version == "2.30.0"
        assert len(resp.requires_dist) == 4
