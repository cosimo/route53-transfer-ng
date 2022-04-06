"""
Unit tests for DNS records serialization/deserialization
"""

import pytest
import yaml

from helpers import (
    load_fixture,
    fixtures_for,
)

from route53_transfer.models import ContinentCodeEnum, R53Record, ResourceRecord, GeoLocationModel


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


def test_deserialize_geolocation_routing_policy():
    records = load_fixture(fixture_filename="geolocation.yaml")
    assert len(records) == 3

    geo_rp_default, geo_rp_se, geo_rp_africa = records

    assert geo_rp_default.Name == "geo1.example.com."
    assert geo_rp_default.TTL is None
    assert geo_rp_default.Type == "A"
    assert len(geo_rp_default.ResourceRecords) == 1
    assert geo_rp_default.GeoLocation.CountryCode == "*"

    assert geo_rp_se.Name == "geo2.example.com."
    assert geo_rp_se.TTL is None
    assert geo_rp_se.Type == "A"
    assert geo_rp_se.ResourceRecords[0].Value == "127.0.0.3"
    assert geo_rp_se.GeoLocation.CountryCode == "SE"

    assert geo_rp_africa.Name == "geo3.example.com."
    assert geo_rp_africa.TTL is None
    assert geo_rp_africa.Type == "A"
    assert geo_rp_africa.ResourceRecords[0].Value == "127.0.0.4"
    assert geo_rp_africa.GeoLocation.CountryCode is None
    assert geo_rp_africa.GeoLocation.ContinentCode == ContinentCodeEnum.Africa


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

    record_dict = r.dict(exclude_none=True)
    record_yaml = yaml.safe_dump(record_dict)

    assert record_yaml is not None
    assert "ContinentCode: EU" in record_yaml
