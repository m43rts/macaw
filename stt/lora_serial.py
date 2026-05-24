import serial
import re


def send_lora(ser: serial.Serial, message: str) -> bool:
    """
    Send a message through the LoRa device via serial.

    The device expects lines starting with "send:" to trigger a LoRa transmission.

    Args:
        ser:     An open serial.Serial instance connected to the LoRa device.
        message: The payload string to transmit over LoRa.

    Returns:
        True if the device acknowledged a successful transmission, False otherwise.
    """
    command = f"send:{message}\n"
    ser.write(command.encode())
    ser.flush()

    # Read lines until we see the TX result or give up
    tx_last_line = False
    for _ in range(20):
        line = ser.readline().decode(errors="replace").strip()
        print(f"> {line}")
        if line:
            if "TX" in line and "OK" in line:
                return True
            elif "TX" in line:
                tx_last_line = True
            elif "OK" in line and tx_last_line:
                return True
            elif "fail" in line:
                return False
            else:
                tx_last_line = False
        else:
            tx_last_line = False

    return False


def read_lora(ser: serial.Serial, timeout: float = 10.0) -> str | None:
    """
    Wait for and parse an incoming LoRa packet from the device.

    The device prints:
        RX [<message>]

    Args:
        ser:     An open serial.Serial instance connected to the LoRa device.
        timeout: How long to wait for a packet, in seconds.

    Returns:
        The received message string, or None if no packet arrived within the timeout.
    """
    original_timeout = ser.timeout
    ser.timeout = timeout

    try:
        while True:
            line = ser.readline().decode(errors="replace").strip()
            if not line:
                # readline timed out
                break

            rx_match = re.match(r"RX \[(.+)\]", line)
            if rx_match:
                return rx_match.group(1)
    finally:
        ser.timeout = original_timeout

    return None

if __name__ == "__main__":
    # Example usage
    with serial.Serial("/dev/ttyUSB0", 115200, timeout=1) as ser:
        if send_lora(ser, "Hello, LoRa!"):
            print("Message sent successfully.")
        else:
            print("Failed to send message.")

        print("Waiting for incoming LoRa packets...")
        received = read_lora(ser, timeout=30)
        if received is not None:
            print(f"Received LoRa message: {received}")
        else:
            print("No LoRa packet received within timeout.")