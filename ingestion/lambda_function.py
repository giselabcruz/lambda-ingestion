import json
import boto3
import os
import csv
import logging
from neo4j import GraphDatabase

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')

# Neo4j connection configuration
NEO4J_URI = os.environ.get('NEO4J_URI')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD')

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

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
                
                process_csv_to_neo4j(download_path)
                        
        return {
            'statusCode': 200,
            'body': json.dumps('Ingestion successful')
        }

    except Exception as e:
        logger.error(f"Error processing event: {e}")
        raise e

def process_csv_to_neo4j(file_path):
    try:
        with driver.session() as session:
            with open(file_path, 'r', encoding='utf-8') as f:
                csv_reader = csv.DictReader(f)
                
                for row in csv_reader:
                    session.execute_write(create_ticket_node, row)
                    
        logger.info(f"Successfully processed {file_path} into Neo4j")

    except Exception as e:
        logger.error(f"Error writing to Neo4j for file {file_path}: {e}")
        raise e

def create_ticket_node(tx, row):
    """
    Creates a Ticket node and relationships in Neo4j.
    Creates relationships between Ticket, Product, Category, Store, and Basket.
    """
    query = """
    MERGE (p:Product {name: $product})
    MERGE (c:Category {name: $category})
    MERGE (s:Store {name: $store})
    MERGE (b:Basket {id: $basket_id})
    CREATE (t:Ticket {
        ticket_id: $ticket_id,
        timestamp: $timestamp,
        quantity: $quantity
    })
    CREATE (t)-[:CONTAINS]->(p)
    CREATE (t)-[:IN_CATEGORY]->(c)
    CREATE (t)-[:PURCHASED_AT]->(s)
    CREATE (t)-[:PART_OF]->(b)
    CREATE (p)-[:BELONGS_TO]->(c)
    """
    tx.run(query, 
           ticket_id=row['ticket_id'],
           product=row['product'],
           basket_id=row['basket_id'],
           timestamp=row['timestamp'],
           category=row['category'],
           quantity=int(row['quantity']),
           store=row['store'])
