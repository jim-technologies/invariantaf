#!/usr/bin/env python3
"""Generate Bybit proto + runtime metadata from OpenAPI explorer YAML files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

import yaml

HTTP_METHODS = ("get", "post", "put", "delete", "patch")
SERVICE_FILES = (
    "account.yaml",
    "asset.yaml",
    "backup.yaml",
    "lt.yaml",
    "market.yaml",
    "position.yaml",
    "spot-margin-uta.yaml",
    "trade.yaml",
    "user.yaml",
)
PROTO_OUT = Path("proto/bybit/v1/bybit.proto")
META_OUT = Path("src/bybit_mcp/spec_meta.py")

PROTO_KEYWORDS = {
    "syntax",
    "import",
    "weak",
    "public",
    "package",
    "option",
    "optional",
    "required",
    "repeated",
    "oneof",
    "map",
    "reserved",
    "rpc",
    "returns",
    "service",
    "message",
    "enum",
    "extensions",
    "to",
    "max",
    "group",
}


def _pascal_case(value: str) -> str:
    chunks = re.split(r"[^A-Za-z0-9]+", value)
    out = "".join(chunk[:1].upper() + chunk[1:] for chunk in chunks if chunk)
    if not out:
        out = "Method"
    if out[0].isdigit():
        out = f"M{out}"
    return out


def _service_prefix_from_filename(filename: str) -> str:
    return "".join(_pascal_case(part) for part in filename.removesuffix(".yaml").split("-"))


def _service_name_from_filename(filename: str) -> str:
    return f"Bybit{_service_prefix_from_filename(filename)}Service"


def _sanitize_identifier(name: str) -> str:
    ident = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not ident:
        ident = "field"
    if ident[0].isdigit():
        ident = f"f_{ident}"
    if ident in PROTO_KEYWORDS:
        ident = f"{ident}_field"
    return ident


@dataclass
class FieldDef:
    name: str
    proto_type: str
    number: int
    repeated: bool = False
    optional: bool = False
    comment: str = ""


@dataclass
class MessageDef:
    name: str
    fields: list[FieldDef] = field(default_factory=list)


@dataclass
class TypeRef:
    proto_type: str
    kind: str
    repeated: bool = False


@dataclass
class Operation:
    service_name: str
    service_prefix: str
    method_name: str
    request_name: str
    http_method: str
    path: str
    summary: str
    has_body: bool
    private: bool


class Generator:
    def __init__(self) -> None:
        self._messages: dict[str, MessageDef] = {}
        self._message_name_counts: dict[str, int] = {}
        self._operations: list[Operation] = []
        self._service_ops: dict[str, list[Operation]] = {}

    def run(self) -> None:
        for filename in SERVICE_FILES:
            self._read_service_file(filename)

        proto_text = self._render_proto()
        PROTO_OUT.parent.mkdir(parents=True, exist_ok=True)
        PROTO_OUT.write_text(proto_text)

        meta_text = self._render_meta()
        META_OUT.parent.mkdir(parents=True, exist_ok=True)
        META_OUT.write_text(meta_text)

        print(f"generated {PROTO_OUT} ({len(self._operations)} operations)")
        print(f"generated {META_OUT}")

    def _read_service_file(self, filename: str) -> None:
        full_path = Path("openapi/v5") / filename
        data = yaml.safe_load(full_path.read_text())
        if not isinstance(data, dict):
            return

        if "paths" in data and isinstance(data["paths"], dict):
            paths: dict[str, Any] = data["paths"]
        else:
            # backup.yaml in Bybit docs is a raw paths snippet without top-level OpenAPI object.
            paths = {k: v for k, v in data.items() if isinstance(k, str) and k.startswith("/v5/")}

        service_name = _service_name_from_filename(filename)
        service_prefix = _service_prefix_from_filename(filename)
        self._service_ops.setdefault(service_name, [])
        method_names_seen: set[str] = set()

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            for http_method in HTTP_METHODS:
                op = path_item.get(http_method)
                if not isinstance(op, dict):
                    continue

                op_id = str(op.get("operationId") or f"{http_method}_{path}")
                method_name = _pascal_case(op_id)
                if method_name in method_names_seen:
                    suffix = 2
                    candidate = f"{method_name}{suffix}"
                    while candidate in method_names_seen:
                        suffix += 1
                        candidate = f"{method_name}{suffix}"
                    method_name = candidate
                method_names_seen.add(method_name)

                request_name = f"{service_prefix}{method_name}Request"
                request_msg = MessageDef(name=request_name)

                parameters = op.get("parameters") or []
                private = False
                field_names_seen: set[str] = set()

                for param in parameters:
                    if not isinstance(param, dict):
                        continue
                    param_in = str(param.get("in") or "")
                    param_name = str(param.get("name") or "")
                    if param_in == "header":
                        if param_name.lower() in {"apikey", "secret"}:
                            private = True
                        continue
                    if param_in not in {"query", "path"}:
                        continue

                    schema = param.get("schema") if isinstance(param.get("schema"), dict) else {}
                    field = self._field_from_schema(
                        raw_name=param_name,
                        schema=schema,
                        required=bool(param.get("required")),
                        field_no=len(request_msg.fields) + 1,
                        context_name=f"{request_name}{_pascal_case(param_name)}",
                        is_param=True,
                        comment=str(param.get("description") or ""),
                    )
                    if field.name in field_names_seen:
                        continue
                    field_names_seen.add(field.name)
                    request_msg.fields.append(field)

                has_body = False
                request_body = op.get("requestBody") if isinstance(op.get("requestBody"), dict) else None
                if request_body is not None:
                    content = request_body.get("content") if isinstance(request_body.get("content"), dict) else {}
                    body_schema = None
                    for content_type in (
                        "application/json",
                        "application/x-www-form-urlencoded",
                        "application/octet-stream",
                    ):
                        node = content.get(content_type)
                        if isinstance(node, dict) and isinstance(node.get("schema"), dict):
                            body_schema = node["schema"]
                            break
                    if body_schema is None:
                        for node in content.values():
                            if isinstance(node, dict) and isinstance(node.get("schema"), dict):
                                body_schema = node["schema"]
                                break

                    if body_schema is not None:
                        has_body = True
                        body_type = self._schema_to_type(
                            schema=body_schema,
                            context_name=f"{request_name}Body",
                            is_param=False,
                        )
                        request_msg.fields.append(
                            FieldDef(
                                name="body",
                                proto_type=body_type.proto_type,
                                repeated=body_type.repeated,
                                optional=False,
                                number=len(request_msg.fields) + 1,
                                comment="Request body",
                            )
                        )

                self._messages[request_name] = request_msg
                operation = Operation(
                    service_name=service_name,
                    service_prefix=service_prefix,
                    method_name=method_name,
                    request_name=request_name,
                    http_method=http_method.upper(),
                    path=path,
                    summary=str(op.get("summary") or op.get("description") or method_name),
                    has_body=has_body,
                    private=private,
                )
                self._operations.append(operation)
                self._service_ops[service_name].append(operation)

    def _unique_message_name(self, base_name: str) -> str:
        name = _pascal_case(base_name)
        if name not in self._message_name_counts:
            self._message_name_counts[name] = 1
            return name
        self._message_name_counts[name] += 1
        return f"{name}{self._message_name_counts[name]}"

    def _field_from_schema(
        self,
        *,
        raw_name: str,
        schema: dict[str, Any],
        required: bool,
        field_no: int,
        context_name: str,
        is_param: bool,
        comment: str,
    ) -> FieldDef:
        name = _sanitize_identifier(raw_name)
        type_ref = self._schema_to_type(schema=schema, context_name=context_name, is_param=is_param)

        optional = False
        if not required and not type_ref.repeated:
            if type_ref.proto_type in {"string", "bool", "int64", "double"}:
                optional = True

        return FieldDef(
            name=name,
            proto_type=type_ref.proto_type,
            repeated=type_ref.repeated,
            optional=optional,
            number=field_no,
            comment=comment,
        )

    def _schema_to_type(self, *, schema: dict[str, Any], context_name: str, is_param: bool) -> TypeRef:
        schema_type = schema.get("type")

        if is_param and schema_type == "array":
            # Bybit explorer marks enum dropdown params as arrays; wire format is scalar.
            items = schema.get("items") if isinstance(schema.get("items"), dict) else {}
            if isinstance(items.get("enum"), list):
                scalar = self._primitive_proto_type(items.get("type") or "string")
                return TypeRef(proto_type=scalar, kind="scalar")

        if schema_type == "array":
            items = schema.get("items") if isinstance(schema.get("items"), dict) else {}
            item_type = self._schema_to_type(schema=items, context_name=f"{context_name}Item", is_param=False)
            if item_type.proto_type.startswith("map<"):
                return TypeRef(proto_type="google.protobuf.Value", kind="value")
            return TypeRef(proto_type=item_type.proto_type, kind=item_type.kind, repeated=True)

        if schema_type == "object" or "properties" in schema:
            props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
            if props:
                message_name = self._unique_message_name(context_name)
                required = set(schema.get("required") or [])
                msg = MessageDef(name=message_name)

                seen: set[str] = set()
                for prop_name, prop_schema in props.items():
                    if not isinstance(prop_schema, dict):
                        prop_schema = {}
                    field_name = _sanitize_identifier(prop_name)
                    if field_name in seen:
                        continue
                    seen.add(field_name)
                    msg.fields.append(
                        self._field_from_schema(
                            raw_name=prop_name,
                            schema=prop_schema,
                            required=prop_name in required,
                            field_no=len(msg.fields) + 1,
                            context_name=f"{message_name}{_pascal_case(prop_name)}",
                            is_param=False,
                            comment=str(prop_schema.get("description") or ""),
                        )
                    )

                self._messages[message_name] = msg
                return TypeRef(proto_type=message_name, kind="message")

            if isinstance(schema.get("additionalProperties"), dict):
                value_type = self._schema_to_type(
                    schema=schema["additionalProperties"],
                    context_name=f"{context_name}Value",
                    is_param=False,
                )
                if value_type.repeated or value_type.proto_type.startswith("map<"):
                    return TypeRef(proto_type="google.protobuf.Struct", kind="struct")
                return TypeRef(proto_type=f"map<string, {value_type.proto_type}>", kind="map")

            return TypeRef(proto_type="google.protobuf.Struct", kind="struct")

        if schema_type in {"string", "integer", "number", "boolean"}:
            return TypeRef(proto_type=self._primitive_proto_type(schema_type), kind="scalar")

        # OpenAPI explorer occasionally leaves schema type ambiguous.
        return TypeRef(proto_type="google.protobuf.Value", kind="value")

    @staticmethod
    def _primitive_proto_type(schema_type: str) -> str:
        if schema_type == "integer":
            return "int64"
        if schema_type == "number":
            return "double"
        if schema_type == "boolean":
            return "bool"
        return "string"

    @staticmethod
    def _comment_line(value: str) -> str:
        compact = re.sub(r"\s+", " ", value).strip()
        return compact

    def _render_proto(self) -> str:
        lines: list[str] = []
        lines.append('syntax = "proto3";')
        lines.append("")
        lines.append("package bybit.v1;")
        lines.append("")
        lines.append('import "google/api/annotations.proto";')
        lines.append('import "google/protobuf/struct.proto";')
        lines.append("")
        lines.append("// Bybit V5 API (explorer subset) projected as protocol-agnostic RPC tools.")
        lines.append("// Generated from openapi/v5/*.yaml.")
        lines.append("")

        for service_name in sorted(self._service_ops.keys()):
            ops = self._service_ops[service_name]
            lines.append(f"service {service_name} {{")
            for op in ops:
                summary = self._comment_line(op.summary)
                if summary:
                    lines.append(f"  // {summary}")
                lines.append(
                    f"  rpc {op.method_name}({op.request_name}) returns (BybitResponse) {{"
                )
                lines.append("    option (google.api.http) = {")
                lines.append(f"      {op.http_method.lower()}: \"{op.path}\"")
                if op.has_body:
                    lines.append('      body: "body"')
                lines.append("    };")
                lines.append("  }")
                lines.append("")
            lines.append("}")
            lines.append("")

        lines.append("message BybitResponse {")
        lines.append("  optional int64 retCode = 1;")
        lines.append("  string retMsg = 2;")
        lines.append("  google.protobuf.Value result = 3;")
        lines.append("  google.protobuf.Value retExtInfo = 4;")
        lines.append("  optional int64 time = 5;")
        lines.append("}")
        lines.append("")

        for message_name in sorted(self._messages.keys()):
            msg = self._messages[message_name]
            lines.append(f"message {message_name} {{")
            if not msg.fields:
                lines.append("}")
                lines.append("")
                continue

            for fld in msg.fields:
                comment = self._comment_line(fld.comment)
                if comment:
                    lines.append(f"  // {comment}")
                qualifier = ""
                if fld.proto_type.startswith("map<"):
                    qualifier = ""
                elif fld.repeated:
                    qualifier = "repeated "
                elif fld.optional:
                    qualifier = "optional "
                lines.append(
                    f"  {qualifier}{fld.proto_type} {fld.name} = {fld.number};"
                )
            lines.append("}")
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def _render_meta(self) -> str:
        service_names = sorted(self._service_ops.keys())
        all_method_paths = [
            f"/bybit.v1.{op.service_name}/{op.method_name}"
            for op in self._operations
        ]
        private_method_paths = [
            f"/bybit.v1.{op.service_name}/{op.method_name}"
            for op in self._operations
            if op.private
        ]

        lines = [
            '"""Generated Bybit API metadata from openapi/v5/*.yaml."""',
            "",
            "SERVICE_NAMES = [",
        ]
        for name in service_names:
            lines.append(f'    "bybit.v1.{name}",')
        lines.append("]")
        lines.append("")

        lines.append("ALL_METHOD_PATHS = {")
        for item in sorted(all_method_paths):
            lines.append(f'    "{item}",')
        lines.append("}")
        lines.append("")

        lines.append("PRIVATE_METHOD_PATHS = {")
        for item in sorted(private_method_paths):
            lines.append(f'    "{item}",')
        lines.append("}")
        lines.append("")
        lines.append(f"TOOL_COUNT = {len(self._operations)}")
        lines.append("")
        return "\n".join(lines)


def main() -> None:
    Generator().run()


if __name__ == "__main__":
    main()
