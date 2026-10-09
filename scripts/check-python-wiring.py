#!/usr/bin/env python3
"""Check actual Python registration without provider calls or credential loading."""

from __future__ import annotations

import argparse
import ast
import asyncio
import importlib.util
import inspect
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ENV = {
    "PATH",
    "HOME",
    "LD_LIBRARY_PATH",
    "LIBSTDCPP_DIR",
    "UV_PYTHON",
    "UV_CACHE_DIR",
    "UV_LINK_MODE",
    "TMPDIR",
    "SSL_CERT_FILE",
    "LANG",
    "LC_ALL",
}
CREDENTIAL_ARGUMENTS = {"api_key", "api_secret", "api_token", "bot_token", "token"}


def deny_network(event: str, _args: tuple) -> None:
    if event in {
        "socket.connect",
        "socket.bind",
        "socket.getaddrinfo",
        "socket.gethostbyname",
        "socket.gethostbyaddr",
    }:
        raise RuntimeError(f"offline registration attempted network operation: {event}")


async def check_provider(provider: Path) -> int:
    for name in list(os.environ):
        if name not in RUNTIME_ENV:
            del os.environ[name]
    from google.protobuf import descriptor_pb2
    from invariant import Server

    sys.addaudithook(deny_network)
    source = provider / "main.py"
    sys.path.insert(0, str(provider))
    spec = importlib.util.spec_from_file_location("adapter_entrypoint", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load adapter entrypoint")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    namespace = vars(module)
    tree = ast.parse(source.read_text())
    main = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    calls = [node for node in ast.walk(main) if isinstance(node, ast.Call)]
    if any(
        isinstance(node.func, ast.Attribute) and node.func.attr == "register"
        for node in calls
    ):
        raise RuntimeError("entrypoint uses removed generic registration")
    registrars = [
        node
        for node in calls
        if isinstance(node.func, ast.Attribute)
        and node.func.attr.startswith("add_")
        and node.func.attr.endswith("Servicer_to_server")
    ]
    connections = [
        node
        for node in calls
        if isinstance(node.func, ast.Attribute) and node.func.attr == "connect_http"
    ]
    if not registrars and not connections:
        raise RuntimeError("entrypoint declares no native or HTTP registration")
    assignments = {
        node.targets[0].id: node.value
        for node in main.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    }
    descriptor = descriptor_pb2.FileDescriptorSet.FromString(
        (provider / "descriptor.binpb").read_bytes()
    )
    expected = {
        f"{file.package}.{service.name}.{method.name}": method
        for file in descriptor.file
        for service in file.service
        for method in service.method
    }
    descriptor_services = {
        f"{file.package}.{service.name}": service
        for file in descriptor.file
        for service in file.service
    }
    server = Server.from_descriptor(str(provider / "descriptor.binpb"))
    public_proxy = Server.from_descriptor(str(provider / "descriptor.binpb"))
    values = {
        "server": server,
        "public_proxy": public_proxy,
        "base_url": "https://invalid.example",
        "gamma_base": "https://invalid.example",
        "clob_base": "https://invalid.example",
        "data_base": "https://invalid.example",
        "header_provider": None,
        "clob_client": None,
        "signature_type_default": 0,
    }
    services = []

    def resolve(expression):
        if isinstance(expression, ast.Name):
            if expression.id in values:
                return values[expression.id]
            if expression.id.endswith("base_url"):
                return "https://invalid.example"
            if expression.id in assignments:
                values[expression.id] = resolve(assignments[expression.id])
                return values[expression.id]
            return namespace[expression.id]
        if isinstance(expression, ast.Attribute):
            return getattr(resolve(expression.value), expression.attr)
        if isinstance(expression, ast.Constant):
            return expression.value
        if not isinstance(expression, ast.Call):
            raise RuntimeError(
                "registration argument needs an explicit offline binding"
            )
        constructor = resolve(expression.func)
        if not inspect.isclass(constructor):
            raise RuntimeError("registration calls an unsupported constructor helper")
        args = [resolve(argument) for argument in expression.args]
        kwargs = {
            keyword.arg: resolve(keyword.value)
            for keyword in expression.keywords
            if keyword.arg not in CREDENTIAL_ARGUMENTS
        }
        parameters = inspect.signature(constructor).parameters
        for name in CREDENTIAL_ARGUMENTS & parameters.keys():
            kwargs[name] = "fixture"
        if (
            provider.name == "hyperliquid"
            and constructor.__name__ == "HyperliquidService"
        ):
            from hyperliquid.info import Info

            kwargs["info"] = Info(
                "https://invalid.example",
                skip_ws=True,
                meta={"universe": []},
                spot_meta={"tokens": [], "universe": []},
            )
        instance = constructor(*args, **kwargs)
        services.append(instance)
        return instance

    try:
        for call in connections:
            service_name = next(
                keyword.value
                for keyword in call.keywords
                if keyword.arg == "service_name"
            )
            if isinstance(service_name, ast.Name) and service_name.id == "service_name":
                names = namespace["SERVICE_NAMES"]
            else:
                names = [resolve(service_name)]
            for name in names:
                values["service_name"] = name
                compile_call = ast.Expression(call)
                ast.fix_missing_locations(compile_call)
                eval(compile(compile_call, str(source), "eval"), namespace, values)
        for call in registrars:
            if len(call.args) != 2 or call.keywords:
                raise RuntimeError("unexpected generated registration signature")
            servicer = resolve(call.args[0])
            service_name = call.func.attr[len("add_") : -len("Servicer_to_server")]
            matching = [
                service
                for name, service in descriptor_services.items()
                if name.rsplit(".", 1)[-1] == service_name
            ]
            if len(matching) != 1:
                raise RuntimeError(
                    "generated registration has ambiguous service identity"
                )
            for method in matching[0].method:
                terminal = getattr(servicer, method.name)
                if not inspect.iscoroutinefunction(terminal):
                    raise RuntimeError(f"native handler is not async: {method.name}")
            values["__checked_servicer"] = servicer
            checked_call = ast.Call(
                func=call.func,
                args=[ast.Name(id="__checked_servicer", ctx=ast.Load()), call.args[1]],
                keywords=[],
            )
            expression = ast.Expression(checked_call)
            ast.fix_missing_locations(expression)
            eval(compile(expression, str(source), "eval"), namespace, values)
        if set(server.tools) != set(expected):
            raise RuntimeError(
                "entrypoint tool surface differs from canonical descriptor"
            )
        for name, method in expected.items():
            tool = server.tools[name]
            if tool.input_type != method.input_type.lstrip(
                "."
            ) or tool.output_type != method.output_type.lstrip("."):
                raise RuntimeError(f"native message identities differ: {name}")
        return len(expected)
    finally:
        for service in reversed(services):
            close = getattr(service, "aclose", None)
            if close is not None:
                await close()
            for client in vars(service).values():
                if (
                    type(client).__module__.startswith("httpx")
                    and hasattr(client, "is_closed")
                    and not client.is_closed
                ):
                    raise RuntimeError("service did not close its HTTP client")
        await server.stop()
        await public_proxy.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider")
    parser.add_argument("providers", nargs="*")
    args = parser.parse_args()
    if args.provider:
        count = asyncio.run(check_provider(ROOT / args.provider))
        print(
            f"PASS: {args.provider}: {count} canonical async methods; no provider I/O"
        )
        return
    environment = {name: os.environ[name] for name in RUNTIME_ENV if name in os.environ}
    providers = args.providers or sorted(
        path.parent.name for path in ROOT.glob("*/main.py")
    )
    failed = False
    for provider in providers:
        result = subprocess.run(
            [
                "uv",
                "run",
                "--locked",
                "--directory",
                str(ROOT / provider),
                "python",
                str(Path(__file__).resolve()),
                "--provider",
                provider,
            ],
            env=environment,
            check=False,
        )
        failed |= result.returncode != 0
    raise SystemExit(int(failed))


if __name__ == "__main__":
    main()
