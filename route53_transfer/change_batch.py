# encoding: utf-8

class ChangeBatch:
    """
    Represents a single batch/transaction of changes to Route53

    Having such a class simplifies the handling of the change operations as
    we can use `ChangeBatch.add_change()` passing the change operation dict
    as it was returned by `compute_changes()`.
    """
    def __init__(self):
        self._changes = []

    @property
    def changes(self):
        return self._changes

    def add_change(self, change_operation: dict) -> None:
        self._changes.append(change_operation)

    def commit(self, r53, zone):
        """
        Commit the current ChangeBatch to Route53 in a single transaction
        """
        def change_to_rrset(change):
            rrset_dict = change["record"].dict(exclude_none=True)
            return {"Action": change["operation"],
                    "ResourceRecordSet": {**rrset_dict}}

        try:
            changes_list = list(map(change_to_rrset, self.changes))
            # print("changes_list:", changes_list)

            response = r53.change_resource_record_sets(
                HostedZoneId=zone['id'],
                ChangeBatch={
                    'Comment': 'route53-transfer load operation',
                    'Changes': changes_list,
                })

            # Example of response:
            #
            # {'ResponseMetadata':
            #    {'RequestId': 'a4138a44-f95c-4458-b8f3-38d349cc2f6c',
            #     'HTTPStatusCode': 200,
            #     'HTTPHeaders': {'x-amzn-requestid': 'a4138a44-f95c-4458-b8f3-38d349cc2f6c',
            #                     'content-type': 'text/xml',
            #                     'content-length': '332',
            #                     'date': 'Mon, 11 Apr 2022 10:06:49 GMT'},
            #     'RetryAttempts': 0},
            #  'ChangeInfo':
            #    {'Id': '/change/C0258959QK8IOL6B7RLY',
            #     'Status': 'PENDING',
            #     'SubmittedAt': datetime.datetime(2022, 4, 11, 10, 6, 49, 714000, tzinfo=tzutc()),
            #     'Comment': 'route53-transfer load operation'}
            #  }

            is_success = 200 == int(response.get('ResponseMetadata', {}).get('HTTPStatusCode', 0))
            return is_success

        # TODO : catch specific exceptions
        except Exception as error:
            print("Exception :" + str(error))
