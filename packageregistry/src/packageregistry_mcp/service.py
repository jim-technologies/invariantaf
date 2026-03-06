"""PackageRegistryService — wraps NPM and PyPI APIs into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from packageregistry_mcp.gen.packageregistry.v1 import packageregistry_pb2 as pb

_NPM_REGISTRY = "https://registry.npmjs.org"
_NPM_DOWNLOADS = "https://api.npmjs.org"
_PYPI_BASE = "https://pypi.org"
_PYPISTATS_BASE = "https://pypistats.org"


class PackageRegistryService:
    """Implements PackageRegistryService RPCs via NPM and PyPI APIs."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _get(self, url: str, params: dict | None = None) -> Any:
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    # --- NPM RPCs ---

    def SearchNPM(self, request: Any, context: Any = None) -> pb.SearchNPMResponse:
        size = request.size or 20
        raw = self._get(f"{_NPM_REGISTRY}/-/v1/search", params={
            "text": request.query,
            "size": size,
        })
        resp = pb.SearchNPMResponse()
        resp.total = raw.get("total", 0)
        for obj in raw.get("objects", []):
            pkg = obj.get("package", {})
            links = pkg.get("links", {})
            publisher = pkg.get("publisher", {})
            resp.results.append(pb.NPMSearchResult(
                name=pkg.get("name", ""),
                version=pkg.get("version", ""),
                description=pkg.get("description", ""),
                keywords=pkg.get("keywords", []) or [],
                date=pkg.get("date", ""),
                publisher=publisher.get("username", ""),
                homepage=links.get("homepage", ""),
                repository=links.get("repository", ""),
            ))
        return resp

    def GetNPMPackage(self, request: Any, context: Any = None) -> pb.GetNPMPackageResponse:
        raw = self._get(f"{_NPM_REGISTRY}/{request.name}")
        dist_tags = raw.get("dist-tags", {})
        latest = dist_tags.get("latest", "")
        time_map = raw.get("time", {})
        maintainers = raw.get("maintainers", []) or []
        repo = raw.get("repository", {}) or {}
        repo_url = repo.get("url", "") if isinstance(repo, dict) else str(repo)

        resp = pb.GetNPMPackageResponse(
            name=raw.get("name", ""),
            latest_version=latest,
            description=raw.get("description", ""),
            license=raw.get("license", "") if isinstance(raw.get("license"), str) else "",
            homepage=raw.get("homepage", "") or "",
            repository_url=repo_url,
            created=time_map.get("created", ""),
            last_modified=time_map.get("modified", ""),
        )
        for tag, ver in dist_tags.items():
            resp.dist_tags[tag] = ver
        for m in maintainers:
            resp.maintainers.append(pb.NPMMaintainer(
                name=m.get("name", ""),
                email=m.get("email", ""),
            ))
        return resp

    def GetNPMDownloads(self, request: Any, context: Any = None) -> pb.GetNPMDownloadsResponse:
        raw = self._get(f"{_NPM_DOWNLOADS}/downloads/point/last-week/{request.name}")
        return pb.GetNPMDownloadsResponse(
            package_name=raw.get("package", ""),
            downloads=raw.get("downloads", 0),
            start_date=raw.get("start", ""),
            end_date=raw.get("end", ""),
        )

    def GetNPMVersions(self, request: Any, context: Any = None) -> pb.GetNPMVersionsResponse:
        raw = self._get(f"{_NPM_REGISTRY}/{request.name}")
        time_map = raw.get("time", {})
        versions_map = raw.get("versions", {})
        resp = pb.GetNPMVersionsResponse(package_name=raw.get("name", ""))
        for ver in versions_map:
            resp.versions.append(pb.NPMVersionInfo(
                version=ver,
                date=time_map.get(ver, ""),
            ))
        return resp

    def GetNPMDependencies(self, request: Any, context: Any = None) -> pb.GetNPMDependenciesResponse:
        raw = self._get(f"{_NPM_REGISTRY}/{request.name}")
        dist_tags = raw.get("dist-tags", {})
        target_version = request.version or dist_tags.get("latest", "")
        versions = raw.get("versions", {})
        version_data = versions.get(target_version, {})

        resp = pb.GetNPMDependenciesResponse(
            package_name=raw.get("name", ""),
            version=target_version,
        )
        for dep_name, dep_ver in (version_data.get("dependencies") or {}).items():
            resp.dependencies.append(pb.Dependency(name=dep_name, version_spec=dep_ver))
        for dep_name, dep_ver in (version_data.get("devDependencies") or {}).items():
            resp.dev_dependencies.append(pb.Dependency(name=dep_name, version_spec=dep_ver))
        for dep_name, dep_ver in (version_data.get("peerDependencies") or {}).items():
            resp.peer_dependencies.append(pb.Dependency(name=dep_name, version_spec=dep_ver))
        return resp

    # --- PyPI RPCs ---

    def GetPyPIPackage(self, request: Any, context: Any = None) -> pb.GetPyPIPackageResponse:
        raw = self._get(f"{_PYPI_BASE}/pypi/{request.name}/json")
        info = raw.get("info", {})
        project_urls = info.get("project_urls") or {}
        resp = pb.GetPyPIPackageResponse(
            name=info.get("name", ""),
            version=info.get("version", ""),
            summary=info.get("summary", "") or "",
            description=info.get("description", "") or "",
            author=info.get("author", "") or "",
            author_email=info.get("author_email", "") or "",
            license=info.get("license", "") or "",
            home_page=info.get("home_page", "") or "",
            requires_python=info.get("requires_python", "") or "",
            classifiers=info.get("classifiers", []) or [],
        )
        for label, url in project_urls.items():
            resp.project_urls.append(pb.PyPIProjectURL(label=label, url=url))
        return resp

    def GetPyPIVersion(self, request: Any, context: Any = None) -> pb.GetPyPIVersionResponse:
        raw = self._get(f"{_PYPI_BASE}/pypi/{request.name}/{request.version}/json")
        info = raw.get("info", {})
        releases = raw.get("releases", {})
        version_files = releases.get(request.version, [])
        upload_date = ""
        if version_files:
            upload_date = version_files[0].get("upload_time", "")
        return pb.GetPyPIVersionResponse(
            name=info.get("name", ""),
            version=info.get("version", ""),
            summary=info.get("summary", "") or "",
            author=info.get("author", "") or "",
            license=info.get("license", "") or "",
            requires_python=info.get("requires_python", "") or "",
            requires_dist=info.get("requires_dist", []) or [],
            upload_date=upload_date,
        )

    def GetPyPIReleases(self, request: Any, context: Any = None) -> pb.GetPyPIReleasesResponse:
        raw = self._get(f"{_PYPI_BASE}/pypi/{request.name}/json")
        releases = raw.get("releases", {})
        resp = pb.GetPyPIReleasesResponse(package_name=raw.get("info", {}).get("name", ""))
        for ver, files in releases.items():
            upload_date = ""
            if files:
                upload_date = files[0].get("upload_time", "")
            resp.releases.append(pb.PyPIReleaseInfo(
                version=ver,
                upload_date=upload_date,
            ))
        return resp

    def GetPyPIDownloads(self, request: Any, context: Any = None) -> pb.GetPyPIDownloadsResponse:
        raw = self._get(f"{_PYPISTATS_BASE}/api/packages/{request.name}/recent")
        data = raw.get("data", {})
        return pb.GetPyPIDownloadsResponse(
            package_name=raw.get("package", "") or request.name,
            last_day=data.get("last_day", 0),
            last_week=data.get("last_week", 0),
            last_month=data.get("last_month", 0),
        )

    def GetPyPIDependencies(self, request: Any, context: Any = None) -> pb.GetPyPIDependenciesResponse:
        if request.version:
            raw = self._get(f"{_PYPI_BASE}/pypi/{request.name}/{request.version}/json")
        else:
            raw = self._get(f"{_PYPI_BASE}/pypi/{request.name}/json")
        info = raw.get("info", {})
        return pb.GetPyPIDependenciesResponse(
            package_name=info.get("name", ""),
            version=info.get("version", ""),
            requires_dist=info.get("requires_dist", []) or [],
            requires_python=info.get("requires_python", "") or "",
        )
