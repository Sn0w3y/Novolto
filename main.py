from pymodbus.client import ModbusTcpClient
import struct
import logging

# Setup basic configuration for logging
logging.basicConfig(filename='../modbus_monitor.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Define connection parameters
HOST = '192.168.178.198'
PORT = 502

# Register map definitions
registers = {
    'state': {'address': 30, 'type': 'uint32', 'length': 2, 'unit': '', 'description': 'State', 'access': 'rw'},
    'sptw': {'address': 32, 'type': 'float', 'length': 2, 'unit': '°C', 'description': 'Target Water Temperature', 'access': 'rw'},
    'sptwh': {'address': 34, 'type': 'float', 'length': 2, 'unit': 'K', 'description': 'Hysteresis Water Temperature', 'access': 'rw'},
    'spp': {'address': 36, 'type': 'uint32', 'length': 2, 'unit': 'W', 'description': 'Target Heating Power', 'access': 'rw'},
    'ni': {'address': 38, 'type': 'uint32', 'length': 2, 'unit': 'ms', 'description': 'Soldering Interval', 'access': 'rw'}
}

def read_float(client, address, length):
    """Read a float from a Modbus device."""
    response = client.read_holding_registers(address, length)
    if response.isError():
        logging.error(f"Error reading address {address}")
        return None
    raw_value = response.registers
    byte_string = struct.pack('>HH', raw_value[0], raw_value[1])
    return struct.unpack('>f', byte_string)[0]

def read_uint32(client, address, length):
    """Read a 32-bit unsigned integer from a Modbus device."""
    response = client.read_holding_registers(address, length)
    if response.isError():
        logging.error(f"Error reading address {address}")
        return None
    return (response.registers[0] << 16) | response.registers[1]

def write_float(client, address, value):
    """Write a float to a Modbus device."""
    byte_string = struct.pack('>f', value)
    register_values = struct.unpack('>HH', byte_string)
    logging.info(f"Writing to address {address}: registers {register_values}")
    response = client.write_registers(address, register_values)
    if response.isError():
        logging.error(f"Error writing to address {address}")
        return False
    return True

def write_uint32(client, address, value):
    """Write a 32-bit unsigned integer to a Modbus device."""
    register_values = [(value >> 16) & 0xFFFF, value & 0xFFFF]
    logging.info(f"Writing to address {address}: registers {register_values}")
    response = client.write_registers(address, register_values)
    if response.isError():
        logging.error(f"Error writing to address {address}")
        return False
    return True

def read_all_values(client):
    """Read all values from the registers and log them."""
    for key, reg in registers.items():
        if reg['access'] in ['r', 'rw']:
            if reg['type'] == 'float':
                value = read_float(client, reg['address'], reg['length'])
            elif reg['type'] == 'uint32':
                value = read_uint32(client, reg['address'], reg['length'])

            if value is not None:
                print(f"{reg['description']} ({reg['address']}) = {value} {reg['unit']}")
                logging.info(f"{reg['description']} ({reg['address']}) = {value} {reg['unit']}")
            else:
                print(f"Failed to read {reg['description']} ({reg['address']})")
                logging.error(f"Failed to read {reg['description']} ({reg['address']})")

def change_value(client):
    """Allow the user to change values of writable registers."""
    print("\nAvailable registers to modify:")
    for key, reg in registers.items():
        if reg['access'] == 'rw':
            print(f"{key}: {reg['description']} ({reg['address']}) - {reg['unit']}")

    while True:
        reg_key = input("\nEnter the register key to modify (or 'q' to quit): ")
        if reg_key == 'q':
            break
        if reg_key not in registers or registers[reg_key]['access'] != 'rw':
            print("Invalid key. Please try again.")
            continue

        reg = registers[reg_key]
        if reg['type'] == 'float':
            new_value = float(input(f"Enter new value for {reg_key} ({reg['unit']}): "))
        elif reg['type'] == 'uint32':
            new_value = int(input(f"Enter new value for {reg_key} ({reg['unit']}): "))

        if reg['type'] == 'float':
            success = write_float(client, reg['address'], new_value)
        elif reg['type'] == 'uint32':
            success = write_uint32(client, reg['address'], new_value)

        if success:
            logging.info(f"Successfully updated {reg['description']} to {new_value} {reg['unit']}")
            print(f"Successfully updated {reg['description']} to {new_value} {reg['unit']}")
        else:
            print("Failed to update the value. Please check the input.")

def control_heating(client):
    """Control the heating system based on user inputs."""
    try:
        target_power = int(input("Enter target heating power (W): "))
        system_state = int(input("Enter system state (e.g., 1 to turn on, 0 to turn off): "))
        if write_uint32(client, registers['spp']['address'], target_power) and write_uint32(client, registers['state']['address'], system_state):
            logging.info(f"Updated heating system: Power={target_power}W, State={system_state}")
            print(f"Updated heating system: Power={target_power}W, State={system_state}")
    except ValueError:
        print("Invalid input. Please enter numeric values.")

def main():
    """Main function to handle Modbus client interactions."""
    client = ModbusTcpClient(HOST, port=PORT)
    client.connect()

    print("Initial values:")
    read_all_values(client)

    menu_options = {
        '1': "Monitor values",
        '2': "Change values",
        '3': "Control heating",
        '4': "Exit"
    }

    while True:
        print("\nMenu:")
        for key, option in menu_options.items():
            print(f"{key}. {option}")
        choice = input("Enter your choice: ")

        if choice == '1':
            print("Current values:")
            read_all_values(client)
        elif choice == '2':
            change_value(client)
        elif choice == '3':
            control_heating(client)
        elif choice == '4':
            break
        else:
            print("Invalid choice. Please try again.")

    client.close()

if __name__ == "__main__":
    main()
