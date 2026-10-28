# === BLOCK: imports_dynamodb ===
# DynamoDB imports — include when orchestration_type="dynamodb" deps exist
from airflow.providers.amazon.aws.hooks.dynamodb import DynamoDBHook
from boto3.dynamodb.conditions import Key, Attr
# === END BLOCK ===
