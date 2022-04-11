# encoding: utf-8

"""
route53-transfer-ng
"""

from __future__ import print_function
from collections import defaultdict

import sys
import time
from datetime import datetime
from os import environ

import boto3

from route53_transfer.models import R53Record
from route53_transfer.serialization import read_records, write_records
from route53_transfer.change_batch import ChangeBatch


def exit_with_error(error):
    sys.stderr.write(error)
    sys.exit(1)


def get_zone(r53_client, zone_name, vpc):
    """
    {
        "HostedZones": [
            {
                "CallerReference": "...",
                "Config": {
                    "Comment": "Comment1",
                    "PrivateZone": false
                },
                "Id": "/hostedzone/ZA...",
                "Name": "example.com.",
                "ResourceRecordSetCount": 100
            },
            {
                "CallerReference": "...",
                "Config": {
                    "PrivateZone": false
                },
                "Id": "/hostedzone/Z1...",
                "Name": "example.org.",
                "ResourceRecordSetCount": 21
            },
            {
                "CallerReference": "...",
                "Config": {
                    "Comment": "",
                    "PrivateZone": false
                },
                "Id": "/hostedzone/Z0...",
                "Name": "example.net.",
                "ResourceRecordSetCount": 14
            }
        ],
        "IsTruncated": false,
        "MaxItems": "100",
        "ResponseMetadata": {
            "HTTPHeaders": {
                "content-length": "1077",
                "content-type": "text/xml",
                "date": "Tue, 22 Mar 2022 13:18:00 GMT",
                "x-amzn-requestid": "61554652-b58d-4918-9024-697e4eb51cf2"
            },
            "HTTPStatusCode": 200,
            "RequestId": "61554652-b58d-4918-9024-697e4eb51cf2",
            "RetryAttempts": 0
        }
    }
    """
    paginator = r53_client.get_paginator('list_hosted_zones')
    hosted_zones = []

    for page in paginator.paginate():
        hosted_zones.extend(page['HostedZones'])

    list_private_zones = vpc is not None and vpc.get('is_private')
    requested_vpc_id = vpc.get('id') if vpc else None
    matching_zones = []

    for zone in hosted_zones:
        is_private = zone['Config']['PrivateZone']
        if zone['Name'] != zone_name + '.':
            continue

        if (is_private and list_private_zones) \
                or (not is_private and not list_private_zones):
            matching_zones.append(zone)

    for zone in matching_zones:
        data = {
            'id': zone.get('Id', '').replace('/hostedzone/', ''),
            'name': zone.get('Name'),
        }
        if not list_private_zones:
            return data

        zone_id = data.get('id')
        z = r53_client.get_hosted_zone(Id=zone_id)
        # TODO validate
        z_vpc_id = z.get('HostedZone', {}) \
            .get('VPCs', {}) \
            .get('VPC', {}) \
            .get('VPCId', '')
        if requested_vpc_id and z_vpc_id == requested_vpc_id:
            return data
    else:
        return None


def create_zone(r53_client, zone_name, vpc):
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", datetime.utcnow().utctimetuple())
    r53_client.create_hosted_zone(
        Name=zone_name,
        VPC={
            "VPCRegion": vpc.get("region"),
            "VPCId": vpc.get("id"),
        },
        HostedZoneConfig={
            "Comment": "autogenerated by route53-transfer @ {}".format(ts),
            "PrivateZone": vpc.get("is_private"),
        }
    )
    return get_zone(r53_client, zone_name, vpc)


def skip_apex_soa_ns(zone, records):
    """
    Name: test.example.com.
    ResourceRecords:
    - Value: ns-550.awsdns-04.net.
    - Value: ns-1248.awsdns-28.org.
    - Value: ns-176.awsdns-22.com.
    - Value: ns-1929.awsdns-49.co.uk.
    TTL: 172800
    Type: NS
    """
    desired_zone_name = zone['name']

    for record in records:
        rec_name = record.Name
        rec_type = record.Type
        if rec_name == desired_zone_name and rec_type in ('SOA', 'NS'):
            continue
        else:
            yield record


def get_file(filename, mode):
    """
    Get a file-like object for a filename and mode.

    If filename is `-` return one of stdin or stdout.
    """
    if filename == '-':
        if mode.startswith('r'):
            return sys.stdin
        elif mode.startswith('w'):
            return sys.stdout
        else:
            raise ValueError('Unknown mode "{}"'.format(mode))
    else:
        return open(filename, mode)


def get_hosted_zone_record_sets(r53_client, zone_id):
    paginator = r53_client.get_paginator('list_resource_record_sets')
    resource_record_sets = []
    for resource_record_set in paginator.paginate(HostedZoneId=zone_id):
        resource_record_sets.extend(resource_record_set['ResourceRecordSets'])

    return list(map(R53Record.from_dict, resource_record_sets))


def load(r53, zone_name, file_in, **kwargs):
    """
    Send DNS records from input file to Route 53.

    Arguments are Route53 connection, zone name, vpc info, and file to open for reading.
    """
    dry_run = kwargs.get('dry_run', False)
    use_upsert = kwargs.get('use_upsert', False)
    vpc = kwargs.get('vpc', {})
    format = kwargs.get('format', 'yaml')

    zone = get_zone(r53, zone_name, vpc)
    if not zone:
        if dry_run:
            print('CREATE ZONE:', zone_name)
            zone = {'name': zone_name, 'id': 'fake-zone-id'}
        else:
            zone = create_zone(r53, zone_name, vpc)

    existing_records = get_hosted_zone_record_sets(r53, zone['id'])
    desired_records = read_records(file_in, format=format)

    changes = compute_changes(zone, existing_records, desired_records,
                              use_upsert=use_upsert)

    if dry_run:
        print("Dry-run requested. No changes are going to be applied")
    else:
        print("Applying changes...")

    n = 1
    for update_batch in changes_to_r53_updates(zone, changes):

        print(f"* Update batch {n} ({len(update_batch.changes)} changes)")
        if dry_run:
            for change in update_batch.changes:
                print("    -", change['operation'], change['record'])
        else:
            update_batch.commit(r53, zone)
        n += 1

    else:
        print("No changes.")

    print("Done.")


def assign_change_priority(zone: dict, change_operations: list) -> None:
    """
    Given a list of change operations derived from the difference of two zones
    files, assign a priority integer to each change operation.

    The priority integer serves two purposes:

    1. Identify the relative order the changes. The target of an alias record
       will have a higher priority, since it needs to be present when we
       commit our change transaction.

    2. Group together all change operations that can be committed together
       in the same ResourceRecordSet change transaction.
    """
    rr_prio = defaultdict(int)

    def is_same_zone(change: dict) -> bool:
        return change["zone"]["id"] == zone["id"]

    def is_alias(change) -> bool:
        record: R53Record = change["record"]
        return record.is_alias() and is_same_zone(change)

    def is_new_alias(change) -> bool:
        return is_alias(change) and change["operation"] in ("CREATE", "UPSERT")

    for change in change_operations:
        if is_new_alias(change):
            record: R53Record = change["record"]
            rr_prio[record.AliasTarget.DNSName] += 1

    for change in change_operations:
        if is_new_alias(change):
            record: R53Record = change["record"]
            rr_prio[record.AliasTarget.DNSName] += rr_prio[record.Name]

    for change in change_operations:
        record: R53Record = change["record"]
        change["prio"] = rr_prio[record.Name]


def changes_to_r53_updates(zone, change_operations):
    """
    Given a list of zone change operations as computed by `compute_changes()`,
    returns a list of R53 update batches. Normally one update batch, that is,
    a `ResourceRecordSets` object, will suffice for all updates. In certain
    cases, when records are aliases and their target records do not already
    exist in a zone, it's necessary to split the zone updates in different
    batches, which have to be committed in two separate operations.

    :param zone: Route53 zone object (dict with `id` and `name`)
    :param change_operations: list of zone change operations as returned by
           `compute_changes()`
    :return: r53_updates: list of ChangeBatch objects
    """

    assign_change_priority(zone, change_operations)

    r53_update_batches = []
    current_batch = ChangeBatch()
    current_prio = None

    for change in sorted(change_operations, key=lambda c: c["prio"], reverse=True):
        order = change["prio"]

        if current_prio is None:
            current_prio = order

        if order != current_prio:
            if current_batch.changes:
                r53_update_batches.append(current_batch)
            current_batch = ChangeBatch()

        current_batch.add_change(change)
        current_prio = order

    if current_batch.changes:
        r53_update_batches.append(current_batch)

    return r53_update_batches


def compute_changes(zone, existing_records, desired_records, use_upsert=False):
    """
    Given two sets of existing and desired resource records, compute the
    list of transactions (ResourceRecordSets changes) that will bring us
    from the existing state to the desired state.

    We need to take into account that we can't commit our changes in a single
    transaction in certain cases. One such cases is when we introduce records
    that are aliases to existing records. Route53 will reject our updates
    if the target record for the alias does not exist yet. The workaround is
    to execute the change in two distinct transactions (ResourceRecordSet
    changes), the first to commit the target resources of all the new aliases
    and the second one for all the other resource records.

    :param zone: Route53 zone object
    :param existing_records: list of rrsets that exist in the r53 zone
    :param desired_records: list of rrsets that we desire as final state
    :param use_upsert: if True, prefers UPSERT operations to CREATE and DELETE
    :return: list of ResourceRecordSet changes to be applied
    """

    existing_records = frozenset(skip_apex_soa_ns(zone, existing_records))
    desired_records = frozenset(skip_apex_soa_ns(zone, desired_records))

    # print("existing:", existing_records)
    # print("desired:", desired_records)

    to_delete = existing_records.difference(desired_records)
    to_add = desired_records.difference(existing_records)
    changes = list()

    def is_in_set(record: R53Record, s: set) -> bool:
        for entry in s:
            if entry.Name == record.Name:
                return True
        return False

    def sort_by_name(s: set):
        return sorted(s, key=lambda r: r.Name)

    if to_add or to_delete:
        for record in sort_by_name(to_add):
            op_type = "UPSERT" if use_upsert and is_in_set(record, to_delete) else "CREATE"
            changes.append({"zone": zone,
                            "operation": op_type,
                            "record": record})

        for record in sort_by_name(to_delete):
            if not (use_upsert and is_in_set(record, to_add)):
                changes.insert(0, {"zone": zone,
                                   "operation": "DELETE",
                                   "record": record})

    return changes


def dump(r53_client, zone_name, output_file, **kwargs):
    """
    Receive DNS records from Route 53 to output file.

    Arguments are Route53 connection, zone name, vpc info, and file to open for writing.
    """
    vpc = kwargs.get('vpc', {})
    format = kwargs.get('format', 'yaml')

    zone = get_zone(r53_client, zone_name, vpc)
    if not zone:
        exit_with_error("ERROR: {} zone {} not found!".format(
            'Private' if vpc.get('is_private') else 'Public',
            zone_name))

    records = get_hosted_zone_record_sets(r53_client, zone['id'])

    output_file.write(write_records(records, format=format))
    output_file.flush()


def zones(r53_client):
    """
    List all Route53 zones in the current account
    """
    paginator = r53_client.get_paginator('list_hosted_zones')

    for hosted_zones_page in paginator.paginate():
        hosted_zones = hosted_zones_page.get("HostedZones", [])

        for zone in hosted_zones:
            zone_id = zone["Id"].replace("/hostedzone/", "")
            zone_name = zone["Name"]
            is_private = zone["Config"]["PrivateZone"]
            comment = zone["Config"].get("Comment", "")

            print("\t".join((zone_id, zone_name, str(is_private), comment)))


def run(params):
    r53_client = boto3.client('route53')
    zone_name = params['<zone>']
    filename = params['<file>']
    format = params.get('--format', 'yaml')

    vpc = {}
    if params.get('--private'):
        vpc['is_private'] = True
        vpc['region'] = params.get('--vpc-region') or environ.get('AWS_DEFAULT_REGION')
        vpc['id'] = params.get('--vpc-id')
        if not vpc.get('region') or not vpc.get('id'):
            exit_with_error("ERROR: Private zones require associated VPC Region and ID "
                            "(--vpc-region, --vpc-id)")
    else:
        vpc['is_private'] = False

    if params.get('dump'):
        # Make it possible to directly use the output of the `zones` command
        if zone_name.endswith('.'):
            zone_name = zone_name[:-1]

        dump(r53_client, zone_name, get_file(filename, 'w'),
             format=format, vpc=vpc)

    elif params.get('load'):
        dry_run = params.get('--dry-run', False)
        use_upsert = params.get('--use-upsert', False)

        load(r53_client, zone_name, get_file(filename, 'r'), vpc=vpc,
             format=format, dry_run=dry_run, use_upsert=use_upsert)

    elif params.get('zones'):
        zones(r53_client)

    else:
        return 1
