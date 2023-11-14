import pika
import json
from datetime import datetime
import subprocess

MAX_ITERACIONES = 3
iteraciones = 0
mes_actual = 10  # Empezamos en octubre (mes 10)

def actuador_ventilacion(temperatura):
    return "Activado" if temperatura > 30 else "Desactivado"

def actuador_luz(temperatura):
    return "Activado" if temperatura < 25 else "Desactivado"

def actuador_agua(humedad):
    return "Activado" if humedad < 50 or humedad > 70 else "Desactivado"

def save_to_json(received, processed):
    global mes_actual
    
    data_to_save = {
        "Fecha": f"2023-{mes_actual}-01",
        "Temperatura Registrada": received['temperatura'],
        "Temperatura": processed['temperatura'],
        "Humedad Registrada": received['humedad'],
        "Humedad": processed['humedad']
    }

    try:
        with open("data.json", 'r') as json_file:
            existing_data = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        existing_data = []

    existing_data.append(data_to_save)
    
    with open("data.json", 'w') as json_file:
        json.dump(existing_data, json_file, indent=4)

    mes_actual += 1

def process_data(ch, method, properties, body):
    global iteraciones
    
    data = eval(body.decode())
    print(f"\nActuadores recibiendo datos {data}")

    original_temperaturas = data['temperatura']
    original_humedades = data['humedad']

    processed_temperaturas = []
    processed_humedades = []

    for t in original_temperaturas:
        estado_ventilacion = actuador_ventilacion(t)
        estado_luz = actuador_luz(t)
        print(f"Actuador de Ventilación: {estado_ventilacion}")
        print(f"Actuador de Luz: {estado_luz}")

        if t < 25:
            processed_temperaturas.append(t + 2)
        elif t > 30:
            processed_temperaturas.append(t - 2)
        else:
            processed_temperaturas.append(t)

    for h in original_humedades:
        estado_agua = actuador_agua(h)
        print(f"Actuador de Agua: {estado_agua}")

        if h < 50:
            processed_humedades.append(h + 2)
        elif h > 70:
            processed_humedades.append(h - 2)
        else:
            processed_humedades.append(h)

    new_data = {
        'temperatura': processed_temperaturas,
        'humedad': processed_humedades
    }
    print(f"Actuadores regresando datos al invernadero {new_data}")

    save_to_json(data, new_data)

    connection = pika.BlockingConnection(pika.ConnectionParameters('172.20.10.4', port=5672))
    channel = connection.channel()
    channel.queue_declare(queue='invernadero_results')
    channel.basic_publish(exchange='', routing_key='invernadero_results', body=str(new_data))
    connection.close()

    iteraciones += 1
    if iteraciones >= MAX_ITERACIONES:
        subprocess.run(["python", "insert.py"])
        ch.stop_consuming()

connection = pika.BlockingConnection(pika.ConnectionParameters('172.20.10.4', port=5672))
channel = connection.channel()
channel.queue_declare(queue='actuadores')
channel.basic_consume(queue='actuadores', on_message_callback=process_data, auto_ack=True)
print('Actuadores esperando datos...')
channel.start_consuming()
