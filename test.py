import serial
import time

def send_command(command):
    with serial.Serial('COM3', 9600, timeout=1) as ser:  # Replace 'COM3' with your serial port
        time.sleep(2)  # Wait for the serial connection to initialize
        ser.write(f'{command}\n'.encode())
        print(f'Sent command: {command}')

if __name__ == "__main__":
    send_command('open')
