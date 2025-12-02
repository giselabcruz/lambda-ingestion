import json
import boto3
import os
import csv
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'Tickets')
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        for record in event['Records']:
            body = json.loads(record['body'])
            
            if 'Records' not in body:
                logger.warning("Skipping message with no S3 Records")
                continue

            for s3_record in body['Records']:
                bucket_name = s3_record['s3']['bucket']['name']
                key = s3_record['s3']['object']['key']
                
                logger.info(f"Processing file: s3://{bucket_name}/{key}")
                
                download_path = f"/tmp/{key.split('/')[-1]}"
                s3_client.download_file(bucket_name, key, download_path)
                
                process_csv_to_dynamodb(download_path)
                        
        return {
            'statusCode': 200,
            'body': json.dumps('Ingestion successful')
        }

    except Exception as e:
        logger.error(f"Error processing event: {e}")
        raise e

def process_csv_to_dynamodb(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            
            with table.batch_writer() as batch:
                for row in csv_reader:
                    item = {
                        'ticket_id': row['ticket_id'],
                        'product': row['product'],
                        'basket_id': row['basket_id'],
                        'timestamp': row['timestamp'],
                        'category': row['category'],
                        'quantity': int(row['quantity']),
                        'store': row['store']
                    }
                    batch.put_item(Item=item)
                    
        logger.info(f"Successfully processed {file_path} into DynamoDB")

    except Exception as e:
        logger.error(f"Error writing to DynamoDB for file {file_path}: {e}")
        raise e
