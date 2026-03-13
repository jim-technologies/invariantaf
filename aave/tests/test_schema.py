"""Schema tests for typed Aave protobuf models."""

from __future__ import annotations

from gen.aave.v1 import aave_pb2


def test_proto_no_struct_or_value_fields():
    disallowed = {"google.protobuf.Struct", "google.protobuf.Value", "google.protobuf.Any"}

    file_desc = aave_pb2.DESCRIPTOR
    for message in file_desc.message_types_by_name.values():
        for field in message.fields:
            msg_type = field.message_type
            if msg_type is None:
                continue
            assert msg_type.full_name not in disallowed, (
                f"{message.full_name}.{field.name} still uses untyped payload {msg_type.full_name}"
            )


def test_rpc_method_count_is_stable():
    total = 0
    for service in aave_pb2.DESCRIPTOR.services_by_name.values():
        total += len(service.methods)
    assert total == 4
