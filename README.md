route53-transfer-ng
===================

Quickly backup and restore AWS Route53 DNS zones.

## Motivation 

`route53-transfer-ng` started as a pull-request to [route53-transfer](https://github.com/cosmin/route53-transfer)
and slowly turned into a port to boto3 of that software, and then finally
a complete rewrite.

I intentionally avoided retaining compatibility with the original code.
In fact, route53-transfer-ng does not use the CSV format anymore, as that
wouldn't easily allow support for all the Route53 routing policies and features.

## Installation

    pip install route53-transfer-ng

## Usage

List all the hosted zones in the current AWS account (use the `AWS_PROFILE`
environment variable to control which account is active):

    route53-transfer-ng zones

Backup the `example.com` zone to a YAML file:

    route53-transfer-ng dump --format yaml example.com example.com.yaml

Use STDOUT instead of a file:

    route53-transfer-ng dump --format yaml example.com -

Restore the `example.com` zone from a YAML file:

    route53-transfer-ng load --format yaml example.com example.com.yaml

To perform a dry run load, add the `--dry-run` option switch.
The command will show the changes that would be made to the R53 zone without
carrying out any operation.

    route53-transfer-ng --dry-run load example.com example.com.yaml

It's possible to use upsert operations when performing a route53 change
operation, instead of the default DELETE + CREATE of recordsets.
To enable this behaviour, supply the `--use-upserts` option.

    route53-transfer-ng --dry-run --use-upserts load example.com example.com.yaml

Use `-` as filename to load from STDIN instead.

Migrate between accounts:

Use the `AWS_PROFILE` environment variable to change the AWS account to be used
by route53-transfer-ng. Dump from one account, load into another.

    AWS_PROFILE=aws_account1 route53-transfer dump example.com test.yaml
    AWS_PROFILE=aws_account2 route53-transfer load example.com test.yaml

## Credits

Thanks to Cosmin Sterejan for the original [route53-transfer](https://github.com/cosmin/route53-transfer)
that I used for some time as-is and then as base and inspiration for this boto3
"ng" version.
