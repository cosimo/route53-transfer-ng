"""
Unit tests for the RecordFormatter class
"""

from route53_transfer.formatter import RecordFormatter
from route53_transfer.models import (
    AliasTargetModel,
    GeoLocationModel,
    R53Record,
    ResourceRecord,
)


def test_batch_summary_empty():
    """Test batch summary with no changes."""
    formatter = RecordFormatter(use_color=False)
    summary = formatter.get_batch_summary([])
    assert summary == "0 changes"


def test_batch_summary_single_change():
    """Test batch summary with single change."""
    formatter = RecordFormatter(use_color=False)
    changes = [{"operation": "CREATE", "record": None, "old_record": None}]
    summary = formatter.get_batch_summary(changes)
    assert summary == "1 change"


def test_batch_summary_multiple_changes():
    """Test batch summary with multiple operation types."""
    formatter = RecordFormatter(use_color=False)
    changes = [
        {"operation": "CREATE", "record": None, "old_record": None},
        {"operation": "CREATE", "record": None, "old_record": None},
        {"operation": "DELETE", "record": None, "old_record": None},
        {"operation": "UPSERT", "record": None, "old_record": None},
    ]
    summary = formatter.get_batch_summary(changes)
    assert "4 changes" in summary
    assert "2 CREATE" in summary
    assert "1 DELETE" in summary
    assert "1 UPSERT" in summary


def test_format_simple_a_record_create():
    """Test formatting a simple A record CREATE operation."""
    formatter = RecordFormatter(use_color=False)

    record = R53Record(
        Name="test.example.com.",
        Type="A",
        TTL=300,
        ResourceRecords=[ResourceRecord(Value="192.0.2.1")],
    )

    change = {"operation": "CREATE", "record": record, "old_record": None}

    output = formatter.format_change(change)

    assert "CREATE" in output
    assert "test.example.com." in output
    assert "A" in output
    assert "TTL: 300" in output
    assert "192.0.2.1" in output
    assert "->" in output


def test_format_delete_operation():
    """Test formatting a DELETE operation."""
    formatter = RecordFormatter(use_color=False)

    record = R53Record(
        Name="old.example.com.",
        Type="A",
        TTL=600,
        ResourceRecords=[ResourceRecord(Value="10.0.0.1")],
    )

    change = {"operation": "DELETE", "record": record, "old_record": None}

    output = formatter.format_change(change)

    assert "DELETE" in output
    assert "old.example.com." in output
    assert "10.0.0.1" in output


def test_format_mx_record_with_multiple_values():
    """Test formatting MX record with multiple values."""
    formatter = RecordFormatter(use_color=False)

    record = R53Record(
        Name="example.com.",
        Type="MX",
        TTL=3600,
        ResourceRecords=[
            ResourceRecord(Value="10 mail1.example.com."),
            ResourceRecord(Value="20 mail2.example.com."),
        ],
    )

    change = {"operation": "CREATE", "record": record, "old_record": None}

    output = formatter.format_change(change)

    assert "MX" in output
    assert "10 mail1.example.com." in output
    assert "20 mail2.example.com." in output


def test_format_alias_record():
    """Test formatting an alias record."""
    formatter = RecordFormatter(use_color=False)

    record = R53Record(
        Name="alias.example.com.",
        Type="A",
        AliasTarget=AliasTargetModel(
            DNSName="target.example.com.",
            HostedZoneId="Z1234567890ABC",
            EvaluateTargetHealth=False,
        ),
    )

    change = {"operation": "CREATE", "record": record, "old_record": None}

    output = formatter.format_change(change)

    assert "ALIAS" in output
    assert "alias.example.com." in output
    assert "target.example.com." in output
    assert "Z1234567890ABC" in output


def test_format_weighted_routing_policy():
    """Test formatting record with weighted routing policy."""
    formatter = RecordFormatter(use_color=False)

    record = R53Record(
        Name="weighted.example.com.",
        Type="A",
        TTL=300,
        SetIdentifier="weight-1",
        Weight=70,
        ResourceRecords=[ResourceRecord(Value="10.0.0.1")],
    )

    change = {"operation": "CREATE", "record": record, "old_record": None}

    output = formatter.format_change(change)

    assert "weighted.example.com." in output
    assert "SetIdentifier: weight-1" in output
    assert "Weight: 70" in output


def test_format_geolocation_routing_policy():
    """Test formatting record with geolocation routing policy."""
    formatter = RecordFormatter(use_color=False)

    record = R53Record(
        Name="geo.example.com.",
        Type="A",
        TTL=300,
        SetIdentifier="geo-sweden",
        GeoLocation=GeoLocationModel(CountryCode="SE"),
        ResourceRecords=[ResourceRecord(Value="10.0.0.1")],
    )

    change = {"operation": "CREATE", "record": record, "old_record": None}

    output = formatter.format_change(change)

    assert "geo.example.com." in output
    assert "GeoLocation" in output
    assert "SE" in output


def test_format_failover_routing_policy():
    """Test formatting record with failover routing policy."""
    formatter = RecordFormatter(use_color=False)

    record = R53Record(
        Name="failover.example.com.",
        Type="A",
        TTL=60,
        SetIdentifier="primary",
        Failover="PRIMARY",
        ResourceRecords=[ResourceRecord(Value="10.0.0.1")],
    )

    change = {"operation": "CREATE", "record": record, "old_record": None}

    output = formatter.format_change(change)

    assert "failover.example.com." in output
    assert "Failover: PRIMARY" in output


def test_format_latency_routing_policy():
    """Test formatting record with latency routing policy."""
    formatter = RecordFormatter(use_color=False)

    record = R53Record(
        Name="latency.example.com.",
        Type="A",
        TTL=300,
        SetIdentifier="us-east-1",
        Region="us-east-1",
        ResourceRecords=[ResourceRecord(Value="10.0.0.1")],
    )

    change = {"operation": "CREATE", "record": record, "old_record": None}

    output = formatter.format_change(change)

    assert "latency.example.com." in output
    assert "Region: us-east-1" in output


def test_upsert_with_ttl_change():
    """Test UPSERT operation showing TTL change."""
    formatter = RecordFormatter(use_color=False)

    old_record = R53Record(
        Name="test.example.com.",
        Type="A",
        TTL=300,
        ResourceRecords=[ResourceRecord(Value="192.0.2.1")],
    )

    new_record = R53Record(
        Name="test.example.com.",
        Type="A",
        TTL=600,
        ResourceRecords=[ResourceRecord(Value="192.0.2.1")],
    )

    change = {"operation": "UPSERT", "record": new_record, "old_record": old_record}

    output = formatter.format_change(change)

    assert "UPSERT" in output
    assert "test.example.com." in output
    assert "TTL: 300 -> 600" in output


def test_upsert_with_value_changes():
    """Test UPSERT operation showing value additions and removals."""
    formatter = RecordFormatter(use_color=False)

    old_record = R53Record(
        Name="test.example.com.",
        Type="A",
        TTL=300,
        ResourceRecords=[
            ResourceRecord(Value="10.0.0.1"),
            ResourceRecord(Value="10.0.0.2"),
        ],
    )

    new_record = R53Record(
        Name="test.example.com.",
        Type="A",
        TTL=300,
        ResourceRecords=[
            ResourceRecord(Value="10.0.0.2"),
            ResourceRecord(Value="10.0.0.3"),
        ],
    )

    change = {"operation": "UPSERT", "record": new_record, "old_record": old_record}

    output = formatter.format_change(change)

    assert "UPSERT" in output
    assert "- 10.0.0.1" in output  # Removed
    assert "+ 10.0.0.3" in output  # Added


def test_upsert_with_weight_change():
    """Test UPSERT operation showing routing policy change."""
    formatter = RecordFormatter(use_color=False)

    old_record = R53Record(
        Name="weighted.example.com.",
        Type="A",
        TTL=300,
        SetIdentifier="weight-1",
        Weight=70,
        ResourceRecords=[ResourceRecord(Value="10.0.0.1")],
    )

    new_record = R53Record(
        Name="weighted.example.com.",
        Type="A",
        TTL=300,
        SetIdentifier="weight-1",
        Weight=80,
        ResourceRecords=[ResourceRecord(Value="10.0.0.1")],
    )

    change = {"operation": "UPSERT", "record": new_record, "old_record": old_record}

    output = formatter.format_change(change)

    assert "UPSERT" in output
    assert "Weight: 70 -> 80" in output


def test_upsert_with_alias_target_change():
    """Test UPSERT operation showing alias target change."""
    formatter = RecordFormatter(use_color=False)

    old_record = R53Record(
        Name="alias.example.com.",
        Type="A",
        AliasTarget=AliasTargetModel(
            DNSName="target1.example.com.",
            HostedZoneId="Z1111111111111",
            EvaluateTargetHealth=False,
        ),
    )

    new_record = R53Record(
        Name="alias.example.com.",
        Type="A",
        AliasTarget=AliasTargetModel(
            DNSName="target2.example.com.",
            HostedZoneId="Z2222222222222",
            EvaluateTargetHealth=False,
        ),
    )

    change = {"operation": "UPSERT", "record": new_record, "old_record": old_record}

    output = formatter.format_change(change)

    assert "UPSERT" in output
    assert "- target1.example.com." in output
    assert "Z1111111111111" in output
    assert "+ target2.example.com." in output
    assert "Z2222222222222" in output


def test_format_batch_with_mixed_operations():
    """Test formatting a batch with CREATE, DELETE, and UPSERT."""
    formatter = RecordFormatter(use_color=False)

    create_record = R53Record(
        Name="new.example.com.",
        Type="A",
        TTL=300,
        ResourceRecords=[ResourceRecord(Value="192.0.2.1")],
    )

    delete_record = R53Record(
        Name="old.example.com.",
        Type="A",
        TTL=300,
        ResourceRecords=[ResourceRecord(Value="192.0.2.2")],
    )

    old_upsert_record = R53Record(
        Name="update.example.com.",
        Type="A",
        TTL=300,
        ResourceRecords=[ResourceRecord(Value="192.0.2.3")],
    )

    new_upsert_record = R53Record(
        Name="update.example.com.",
        Type="A",
        TTL=600,
        ResourceRecords=[ResourceRecord(Value="192.0.2.3")],
    )

    changes = [
        {"operation": "CREATE", "record": create_record, "old_record": None},
        {"operation": "DELETE", "record": delete_record, "old_record": None},
        {
            "operation": "UPSERT",
            "record": new_upsert_record,
            "old_record": old_upsert_record,
        },
    ]

    output = formatter.format_batch(changes)

    assert "CREATE" in output
    assert "DELETE" in output
    assert "UPSERT" in output
    assert "new.example.com." in output
    assert "old.example.com." in output
    assert "update.example.com." in output


def test_upsert_multiple_records_same_name_different_types():
    """Test UPSERT with multiple records having same name but different types (e.g., MX and TXT)."""
    formatter = RecordFormatter(use_color=False)

    # Old MX record
    old_mx_record = R53Record(
        Name="example.com.",
        Type="MX",
        TTL=60,
        ResourceRecords=[
            ResourceRecord(Value="10 mail1.example.com."),
            ResourceRecord(Value="20 mail2.example.com."),
        ],
    )

    # New MX record
    new_mx_record = R53Record(
        Name="example.com.",
        Type="MX",
        TTL=60,
        ResourceRecords=[
            ResourceRecord(Value="10 mail1.example.com."),
            ResourceRecord(Value="20 mail3.example.com."),
        ],
    )

    # Old TXT record
    old_txt_record = R53Record(
        Name="example.com.",
        Type="TXT",
        TTL=60,
        ResourceRecords=[
            ResourceRecord(Value='"v=spf1 include:_spf.example.com ~all"')
        ],
    )

    # New TXT record
    new_txt_record = R53Record(
        Name="example.com.",
        Type="TXT",
        TTL=60,
        ResourceRecords=[
            ResourceRecord(Value='"v=spf1 include:_spf.example.com -all"')
        ],
    )

    # Create changes for both records
    mx_change = {
        "operation": "UPSERT",
        "record": new_mx_record,
        "old_record": old_mx_record,
    }

    txt_change = {
        "operation": "UPSERT",
        "record": new_txt_record,
        "old_record": old_txt_record,
    }

    # Format MX change
    mx_output = formatter.format_change(mx_change)
    assert "MX" in mx_output
    assert "- 20 mail2.example.com." in mx_output
    assert "+ 20 mail3.example.com." in mx_output
    # Make sure TXT values don't appear in MX output
    assert "spf1" not in mx_output

    # Format TXT change
    txt_output = formatter.format_change(txt_change)
    assert "TXT" in txt_output
    assert '- "v=spf1 include:_spf.example.com ~all"' in txt_output
    assert '+ "v=spf1 include:_spf.example.com -all"' in txt_output
    # Make sure MX values don't appear in TXT output
    assert "mail1.example.com" not in txt_output
    assert "mail2.example.com" not in txt_output
    assert "mail3.example.com" not in txt_output


def test_upsert_multiple_records_same_name_and_type_different_set_identifiers():
    """Test UPSERT with multiple A records having same name and type but different SetIdentifiers (weighted routing)."""
    formatter = RecordFormatter(use_color=False)

    # Old weighted A record - weight-1
    old_weight1_record = R53Record(
        Name="test.example.com.",
        Type="A",
        TTL=300,
        SetIdentifier="weight-1",
        Weight=70,
        ResourceRecords=[ResourceRecord(Value="10.0.0.1")],
    )

    # New weighted A record - weight-1 (updated weight)
    new_weight1_record = R53Record(
        Name="test.example.com.",
        Type="A",
        TTL=300,
        SetIdentifier="weight-1",
        Weight=80,
        ResourceRecords=[ResourceRecord(Value="10.0.0.1")],
    )

    # Old weighted A record - weight-2
    old_weight2_record = R53Record(
        Name="test.example.com.",
        Type="A",
        TTL=300,
        SetIdentifier="weight-2",
        Weight=30,
        ResourceRecords=[ResourceRecord(Value="10.0.0.2")],
    )

    # New weighted A record - weight-2 (updated IP)
    new_weight2_record = R53Record(
        Name="test.example.com.",
        Type="A",
        TTL=300,
        SetIdentifier="weight-2",
        Weight=30,
        ResourceRecords=[ResourceRecord(Value="10.0.0.3")],
    )

    # Create changes for both weighted records
    weight1_change = {
        "operation": "UPSERT",
        "record": new_weight1_record,
        "old_record": old_weight1_record,
    }

    weight2_change = {
        "operation": "UPSERT",
        "record": new_weight2_record,
        "old_record": old_weight2_record,
    }

    # Format weight-1 change
    weight1_output = formatter.format_change(weight1_change)
    assert "weight-1" in weight1_output
    assert "Weight: 70 -> 80" in weight1_output
    # Since only Weight changed (not IP), the IP shouldn't appear in diff
    # Make sure weight-2 values and changes don't appear in weight-1 output
    assert "weight-2" not in weight1_output
    assert "10.0.0.2" not in weight1_output
    assert "10.0.0.3" not in weight1_output
    assert "Weight: 30" not in weight1_output

    # Format weight-2 change
    weight2_output = formatter.format_change(weight2_change)
    assert "weight-2" in weight2_output
    assert "- 10.0.0.2" in weight2_output
    assert "+ 10.0.0.3" in weight2_output
    # Make sure weight-1 values don't appear
    assert "weight-1" not in weight2_output
    assert "Weight: 70 -> 80" not in weight2_output
