"""
Object-based single table implementation
See https://www.trek10.com/blog/dynamodb-single-table-relational-modeling
https://github.com/trek10inc/ddb-single-table-example
"""

import boto3
from boto3.dynamodb.conditions import Key, Attr
from boto3.dynamodb import types
import decimal
import argparse
import time
import os
import logging
from eib_aws_utils.dynamo_utils import FloatSerializer, FloatDeserializer

from dotenv import load_dotenv, find_dotenv

from unittest.mock import patch

class DDB_Single_Table():
    
    db = None
    db_client = None
    table_name = None
    endpoint_url = None
    table = None
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

# allow to work with Float
# see: https://github.com/boto/boto3/issues/665    
    @patch("boto3.dynamodb.types.TypeSerializer", new=FloatSerializer)
    @patch("boto3.dynamodb.types.TypeDeserializer", new=FloatDeserializer)
    def __init__(self, table_name = None, endpoint_url = None):
        if table_name is None:
            table_name = os.getenv("DYNAMODB_TABLE_NAME")
        if endpoint_url is None:
            endpoint_url = os.getenv("DYNAMODB_ENDPOINT_URL")
        
        self.table_name = table_name
        self.endpoint_url = endpoint_url
        
        self.db = boto3.resource('dynamodb', endpoint_url=endpoint_url)
        self.db_client = boto3.client("dynamodb", endpoint_url=endpoint_url)
        # self.table = self.initialize_table()
        self.table = self.setup_table()
        self.logger.debug("initialized for table {}, endpoint {}".format(self.table_name, self.endpoint_url))


    def setup_table(self):

        try:
            response = self.db_client.describe_table(TableName=self.table_name)
            self.logger.info("table {} already exists.".format(self.table_name))
            return self.db.Table(self.table_name)

        except self.db_client.exceptions.ResourceNotFoundException:
            self.logger.info("table {} not found, creating new...", (self.table_name))
            return self.initialize_table()
                
    def initialize_table(self):
        try:
            table = self.db.create_table(TableName=self.table_name,
                KeySchema=[
                    {
                        'AttributeName': 'pk',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'sk',
                        'KeyType': 'RANGE'
                    },
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'pk',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'sk',
                        'AttributeType': 'S'
                    },
                    {
                    'AttributeName': 'pvalue',
                    'AttributeType': 'S'
                    }
                ],
                GlobalSecondaryIndexes=[
                {
                    'IndexName': 'gsi_1',
                    'KeySchema': [
                            {
                                'AttributeName': 'sk',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'pvalue',
                                'KeyType': 'RANGE'
                            },
                            ],
                            'Projection': {
                                'ProjectionType': 'ALL'
                            },
                            'ProvisionedThroughput': {
                                'ReadCapacityUnits': 10,
                                'WriteCapacityUnits': 10
                            }        
                    },
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                },
                BillingMode='PROVISIONED',
            )
            self.logger.info("Waiting for table to create...")
            table.meta.client.get_waiter('table_exists').wait(TableName=self.table_name)
            return table
        except Exception as e:
            self.logger.info("Create table exception: {}".format(e))
    
    def teardown(self):
        self.logger.info("Deleting the {} table...".format(self.table_name))
        try:
            self.table.delete()
        except Exception as e:
            self.logger.error("Delete table exception: {}".format(e))

    def save_db_record(self, pk, sk, pvalue, **items):
        if pvalue == "":
            pvalue = " "
        if isinstance(items, dict):
            for (key, value) in items.items():  # fix 'empty string' problem in DynamoDB
                if value == "":                 # https://forums.aws.amazon.com/thread.jspa?threadID=90137
                    items[key] = " "
        try:
            table_item = {"pk": pk, "sk": sk, "pvalue": pvalue, **items}
            self.logger.debug("About to store: {}".format(table_item))
            db_response = self.table.put_item(Item=table_item)
            return db_response
        except Exception as e:
            self.logger.error("Save DB record exception: {}".format(e))
            
    def delete_db_record(self, pk, sk):
        try:
            self.logger.debug("About to delete: {} - {}".format(pk, sk))
            db_response = self.table.delete_item(Key={"pk": pk, "sk": sk})
            return db_response
        except Exception as e:
            self.logger.error("Delete DB record exception: {}".format(e))
            
    def get_db_records_by_secondary_key(self, sk, pvalue_condition=None):
        params = {
            "IndexName": "gsi_1",
            "KeyConditionExpression": Key("sk").eq(sk)
        }
        if pvalue_condition is not None:
            params ["KeyConditionExpression"] &= Key("pvalue").eq(pvalue_condition)
        try:
            self.logger.error("query params: {}".format(params))
            db_record = self.table.query(**params)
            db_response = db_record.get("Items", [])
            return db_response
        except Exception as e:
            self.logger.error("Get DB record by secondary key exception: {}".format(e))
                    
    def get_db_record(self, pk, sk):
        try:
            db_record = self.table.get_item(Key={"pk": str(pk), "sk": sk})
            if "Item" in db_record:
                ## TODO: check if token is not expired, generate new using refresh token if needed
                return db_record["Item"]
            else:
                return None    
        except Exception as e:
            self.logger.error("Get DB record exception: {}".format(e))

    def query_db_record(self, pk, pvalue_condition=None):
        try:
            if pvalue_condition is None:
                db_record = self.table.query(
                    KeyConditionExpression=Key("pk").eq(pk)
                )
            else:
                db_record = self.table.scan(
                    IndexName="gsi_1",
                    # KeyConditionExpression=Key("pk").eq(pk),
                    FilterExpression=Key("pk").eq(pk) & Attr("pvalue").eq(pvalue_condition)
                    # ExpressionAttributeValues={
                    #     ":pvalue": {'S': pvalue_condition},
                    # }
                )
            db_response = db_record.get("Items", [])
            return db_response
        except Exception as e:
            self.logger.error("Query DB record list exception: {}".format(e))

    def delete_db_records_by_secondary_key(self, sk):
        try:
            for record in self.get_db_records_by_secondary_key(sk):
                db_response = self.delete_db_record(record["pk"], sk)
                self.logger.debug("delete DB record {}: {}".format(record["pk"], db_response))
        except Exception as e:
            self.logger.error("Delete DB record by secondary key exception: {}".format(e))

def handler():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--teardown", help="delete DynamoDB table", action='store_true')
    args = parser.parse_args()
    
    ddb = DDB_Single_Table()
    
    if args.teardown:
        ddb.teardown()
        
    return ddb
    
if __name__ == "__main__":
    ddb = handler()
