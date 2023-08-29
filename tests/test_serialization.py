"""
Unit tests for DNS records serialization/deserialization
"""

import pytest
import yaml

from helpers import (
    load_fixture,
    fixtures_for,
)

from route53_transfer.models import ContinentCodeEnum, R53Record, ResourceRecord, GeoLocationModel, AliasTargetModel


@pytest.mark.parametrize('fixture', fixtures_for('test1'))
def test_deserialize_simple_record(fixture):
    """
    Test deserialization of a simple A record from YAML/JSON files
    """
    records = load_fixture(fixture_filename=fixture)
    assert len(records) == 1

    simple_a_record = records[0]

    name = simple_a_record.Name
    assert name == "test1.example.com."
    assert name.endswith(".")

    assert simple_a_record.Type == "A"

    assert simple_a_record.TTL == 65

    rr = simple_a_record.ResourceRecords
    assert len(rr) == 1

    rr0_value = rr[0].Value
    assert rr0_value == "127.0.0.99"


def test_deserialize_alias_record():
    records = load_fixture(fixture_filename="alias.yaml")
    assert len(records) == 1

    alias = records[0]

    assert alias.Name == "alias1.example.com."
    assert alias.TTL == 299
    assert alias.Type == "A"
    assert alias.ResourceRecords is None
    assert alias.GeoLocation is None

    alias_target = alias.AliasTarget
    assert alias_target is not None
    assert alias_target.DNSName == "target1.example.com."
    assert alias_target.EvaluateTargetHealth is False
    assert alias_target.HostedZoneId == "A3TCE240BABCDE"


def test_serialize_deserialize_geolocation_eu():
    records = load_fixture(fixture_filename="geolocation_continentcode_eu.yaml")
    assert len(records) == 1

    geo_rp_eu = records[0]

    assert geo_rp_eu.Name == "geo4.example.com."
    assert geo_rp_eu.TTL is None
    assert geo_rp_eu.Type == "A"
    assert geo_rp_eu.ResourceRecords[0].Value == "127.0.0.5"
    assert geo_rp_eu.GeoLocation.CountryCode is None
    assert geo_rp_eu.GeoLocation.ContinentCode == ContinentCodeEnum.Europe

    from route53_transfer.serialization import write_records
    geo_rp_eu_yaml = write_records(records, format="yaml")
    assert geo_rp_eu_yaml is not None

    geo_rp_eu_dict = yaml.safe_load(geo_rp_eu_yaml)[0]
    assert geo_rp_eu_dict["Name"] == "geo4.example.com."
    assert geo_rp_eu_dict["GeoLocation"]["ContinentCode"] == "EU"


def test_serialize_record_with_continent_eu():
    r = R53Record(
        Name="test1.example.com.",
        TTL=300,
        Type="A",
        ResourceRecords=[
            ResourceRecord(Value="127.0.0.11"),
        ],
        GeoLocation=GeoLocationModel(
            ContinentCode=ContinentCodeEnum.Europe,
        ),
    )

    record_dict = r.model_dump(exclude_none=True)
    record_yaml = yaml.safe_dump(record_dict)

    assert record_yaml is not None
    assert "ContinentCode: EU" in record_yaml


def test_serialize_alias_record():
    r = R53Record(
        Name="alias1.example.com.",
        TTL=300,
        Type="A",
        AliasTarget=AliasTargetModel(
            DNSName="target1.example.com.",
            EvaluateTargetHealth=False,
            HostedZoneId="Z2FDTNDATAQYW2",
        ),
    )

    record_dict = r.model_dump(exclude_none=True)
    record_yaml = yaml.safe_dump(record_dict)

    assert record_yaml is not None
    assert "AliasTarget:" in record_yaml
    assert "DNSName: target1.example.com" in record_yaml
