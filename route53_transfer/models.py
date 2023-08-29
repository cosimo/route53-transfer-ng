# encoding: utf-8

from enum import Enum
from pydantic import Field
from typing import List, Optional

from route53_transfer.hashable_model import HashableModel


class AliasTargetModel(HashableModel):

    DNSName: str = Field(
        None,
        description="DNS name of the target host",
        examples=["test1.example.com."],
    )
    EvaluateTargetHealth: bool = Field(
        None,
        description="Whether or not to evaluate the health of the target",
        examples=[False, True],
    )
    HostedZoneId: str = Field(
        None,
        description="Hosted zone ID of the target host",
        examples=["Z0992A3F3Q3HY06FU"],
    )


class ResourceRecord(HashableModel):

    Value: str = Field(
        None,
        description="Value of the resource record",
        examples=["test1.example.com."],
    )


class RegionEnum(str, Enum):
    us_east_1 = "us-east-1"
    us_east_2 = "us-east-2"
    us_west_1 = "us-west-1"
    us_west_2 = "us-west-2"
    ca_central_1 = "ca-central-1"
    ap_northeast_1 = "ap-northeast-1"
    ap_northeast_2 = "ap-northeast-2"
    ap_southeast_1 = "ap-southeast-1"
    ap_southeast_2 = "ap-southeast-2"
    ap_south_1 = "ap-south-1"
    eu_central_1 = "eu-central-1"
    eu_west_1 = "eu-west-1"
    eu_west_2 = "eu-west-2"
    eu_west_3 = "eu-west-3"
    sa_east_1 = "sa-east-1"


class ContinentCodeEnum(str, Enum):
    Africa = "AF"
    Antarctica = "AN"
    Asia = "AS"
    Europe = "EU"
    NorthAmerica = "NA"
    Oceania = "OC"
    SouthAmerica = "SA"


class GeoLocationModel(HashableModel):

    ContinentCode: Optional[str] = Field(
        default=None,
        description="Continent code of the location",
        examples=[ContinentCodeEnum.Antarctica],
    )
    CountryCode: Optional[str] = Field(
        default=None,
        description="Country code or '*' for default or fallback",
        examples=["US"],
    )
    SubdivisionCode: Optional[str] = Field(
        default=None,
        description="Subdivision code of the location",
        examples=["CA"],
    )


class R53Record(HashableModel):

    Name: str = Field(
        None,
        description="Name of the DNS record",
        examples=["test1.example.com."],
    )
    Type: str = Field(
        None,
        description="Type of DNS record",
        examples=["A"],
    )
    TTL: int = Field(
        None,
        description="Time to leave of the DNS record in seconds",
        examples=[60, 300],
    )
    Region: Optional[str] = Field(
        None,
        description="If the record has latency routing policy, this field will"
                    " indicate which AWS region is the record pointing to."
                    " Must be a valid AWS region name",
        examples=["eu-west-1", "us-east-2"],
    )
    GeoLocation: Optional[GeoLocationModel] = None
    AliasTarget: Optional[AliasTargetModel] = None
    ResourceRecords: Optional[List[ResourceRecord]] = None
    SetIdentifier: Optional[str] = Field(
        default=None,
        description="Assigns an arbitrary identifier to the record",
        examples=["rp-geo-default", "europe-main"],
    )
    Weight: Optional[int] = Field(
        default=None,
        description="If the record has weighted routing policy, this field will"
                    " indicate the weight of the record.",
        examples=[0, 100],
    )
    Failover: Optional[str] = Field(
        default=None,
        description="Can be either PRIMARY or SECONDARY",
        examples=["PRIMARY", "SECONDARY"],
    )
    MultiValueAnswer: Optional[bool] = Field(
        default=None,
        examples=[False, True],
    )
    HealthCheckId: Optional[str] = Field(
        default=None,
        description="Unique identifier of the associated health check",
        examples=["ff59b681-c8b6-4039-98ed-0e5b77edc1ac"],
    )
    TrafficPolicyInstanceId: Optional[str] = Field(
        default=None,
        examples=["ff59b681-c8b6-4039-98ed-0e5b77edc1ac"],
    )

    @staticmethod
    def from_dict(record_dict: dict) -> "R53Record":
        return R53Record(**record_dict)

    def is_alias(self) -> bool:
        return self.AliasTarget is not None

    def is_alias_in_zone(self, zone_id: str) -> bool:
        return self.is_alias() and self.AliasTarget.HostedZoneId == zone_id

    def alias_target(self):
        return self.AliasTarget.DNSName if self.is_alias() else None

    def __str__(self):
        dict_ = self.dict(exclude_none=True)
        return str(dict_)
