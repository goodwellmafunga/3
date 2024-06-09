import serial
import time

def send_command(command):
    with serial.Serial('COM6', 9600, timeout=1) as ser:
        time.sleep(2)  # Wait for the serial connection to initialize
        ser.write(f'{command}\n'.encode())

def open_boom_gate():
    send_command('open')
