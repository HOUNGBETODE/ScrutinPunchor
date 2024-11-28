import base64, json, pika
from django.conf import settings

def produce(queue, data):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=settings.RMQ_HOST,
            credentials=pika.PlainCredentials(
                username=settings.RMQ_USER, 
                password=settings.RMQ_PASS
            )
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue=queue)
    channel.basic_publish(
        exchange='', 
        routing_key=queue, 
        body=data
    )
    print(f" [x] Sent '{data}'")
    connection.close()

def deobfuscate_data(data):
    data_splitted = data.split(".")
    random_seed = int(data_splitted[1])
    tokenized_data_shuffled = hex(int(data_splitted[0]))[2:]
    tokenized_data_shuffled_length = len(tokenized_data_shuffled)
    start_index = tokenized_data_shuffled_length - random_seed
    tokenized_data = tokenized_data_shuffled[start_index:] + tokenized_data_shuffled[:start_index]
    tokenized_data_content = bytes.fromhex(tokenized_data).decode()
    return tokenized_data_content