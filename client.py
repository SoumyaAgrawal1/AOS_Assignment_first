import grpc
import battlefield_pb2
import battlefield_pb2_grpc
import random
import time

# Define ANSI escape codes for colors
RED = '\033[91m'
GREEN = '\033[92m'
WHITE = '\033[0m'
YELLOW = '\033[93m'
BLUE = '\033[94m'

def print_guidelines():
    # Prints general guidelines and information(Color coded acc to battlefield simulation)
    print("Welcome to the Battlefield Simulation!")
    print("------------------------------------")
    print("1. The Soldiers and empty cells")
    print(f"{YELLOW}2. Important information")
    print(f"{GREEN}3. Commander")
    print(f"{RED}4. Locations impacted by Missile")
    print(f"{BLUE}5. Broadcasted message")
    print(f"{WHITE}------------------------------------\n\n")

def printLayout(matrix_str, commander_id, max_length):
    # Print the battlefield layout with colors for commander and impact locations
    matrix_rows = matrix_str.split('\n')
    for row in matrix_rows:
        elements = row.split(',')  # Split row using the comma delimiter
        formatted_row = []

        for element in elements:
            if element == 'X':
                # Pad each element to the length of max_length
                element = "{:{width}}".format(element, width=max_length)
                formatted_row.append(f"{RED}{element}{WHITE}")  

            elif element == str(commander_id):
                element = "{:{width}}".format(element, width=max_length)
                formatted_row.append(f"{GREEN}{element}{WHITE}")  

            else:
                # Pad each element to the length of max_length
                formatted_element = "{:{width}}".format(element, width=max_length)
                formatted_row.append(formatted_element)

        formatted_row_str = ' '.join(formatted_row)
        print(formatted_row_str)

def get_valid_integer_input(prompt, error_message, min_value=1, max_value=None):
    # Get integer input from the user with validation
    while True:
        user_input = input(prompt)
        try:
            value = int(user_input)
            if min_value is not None and value < min_value:
                print(error_message)
            elif max_value is not None and value > max_value:
                print(error_message)
            else:
                return value
        except ValueError:
            print("Invalid input. Please enter an integer.")

def print_soldier_info(soldiers):
    # Print information about each soldier
    for soldier_info in soldiers:
        print(f"Soldier {soldier_info.id}: x={soldier_info.x}, y={soldier_info.y}, Speed={soldier_info.Si}, Commander={soldier_info.is_commander}, Alive={soldier_info.is_alive}")

def generate_soldiers(N, M):
    # Generate random soldiers with unique positions
    soldiers = []
    positions = set()

    for i in range(1, M + 1):
        while True:
            x = random.randint(0, N - 1)
            y = random.randint(0, N - 1)
            position = (x, y)

            # Ensure that the position is unique
            if position not in positions:
                Si = random.randint(0, 4)
                is_commander = (i == 1)  # First soldier is the commander(for simplicity)
                soldier = battlefield_pb2.Soldier(id=i, x=x, y=y, Si=Si, is_commander=is_commander, is_alive=True)
                soldiers.append(soldier)
                positions.add(position)
                break

    return soldiers

def connect_to_server():
    # Establish a connection to the server
    stub = None
    while stub is None:
        host = input("Enter the server host (IP address): ")
        port = 50051  # Default port
        server_address = f"{host}:{port}"
        
        try:
            channel = grpc.insecure_channel(server_address)
            stub = battlefield_pb2_grpc.BattlefieldServiceStub(channel)
            
            # Try to get the initial layout to check if the connection has been established
            get_initial_layout_response = stub.GetInitialLayout(battlefield_pb2.GetInitialLayoutRequest())
            print("Connected to the server.")
            return stub
            
        except Exception as e:
            print(f"Could not connect to the server. Please enter a valid IP address without quotes.")
            

def main():
    stub=None
    while stub is None:
        stub=connect_to_server()

    print_guidelines()

    N = get_valid_integer_input("Enter the size of the battlefield (N x N): ", "N should be greater than 4.", min_value=4)
    M = get_valid_integer_input(f"Enter the number of soldiers (M, max {N*N}): ", f"M should be between 9 and {N * N}.", min_value=10, max_value=N*N)

    # Generate soldiers with different x and y values
    soldiers = generate_soldiers(N, M)

    # Initialize the battlefield
    initialize_request = battlefield_pb2.InitializeRequest(n=N, m=M)
    initialize_response = stub.InitializeBattlefield(initialize_request)

    # Send soldiers to the server
    for soldier in soldiers:
        add_soldier_request = battlefield_pb2.AddSoldierRequest(soldier=soldier)
        add_soldier_response = stub.AddSoldier(add_soldier_request)

    # Get the total duration of time (T)
    T = get_valid_integer_input("Enter the total duration of time (T): ", "T should be a positive integer.")

    # Get the time interval for missile launches (t)
    t = get_valid_integer_input("Enter the time interval for missile launches (t): ", "t should be a positive integer.")

    # Convert M to a string and calculate its length(we will use this in pintLayout for padding)
    M_str = str(M)
    max_length = len(M_str)

    #getting the battlefield and soldier information
    get_initial_layout_response = stub.GetInitialLayout(battlefield_pb2.GetInitialLayoutRequest())
    initial_layout = get_initial_layout_response.battlefield_layout
    soldiers = get_initial_layout_response.soldiers

    comm_response = stub.FindCommander(battlefield_pb2.Empty())

    print(f"{WHITE}------------------------------------\n\n")
    print("Iteration 0:")
    printLayout(initial_layout,comm_response.id,max_length)
    print_soldier_info(soldiers)

    # Calculate the number of iterations based on T and t
    num_iterations = T // t
    casualities=0
    for i in range(1, num_iterations + 1):
        print(f"{WHITE}------------------------------------\n")
        x = random.randint(0, N - 1)  # Random x-coordinate
        y = random.randint(0, N - 1)  # Random y-coordinate
        missile_type = random.randint(1, 4)  # Random missile type (1 to 4)

        #find commander id
        comm_response = stub.FindCommander(battlefield_pb2.Empty())

        flag=0
        
        # Check if a commander is present (ID is not -1)
        if comm_response.id !=-1:
            flag=1

            # Notify the clients that a missile is approaching.. sending commander id because only commander can broadcast
            missile_approaching_response = stub.MissileApproaching(
            battlefield_pb2.BroadcastRequest(
            soldier_id=comm_response.id, missile_type=missile_type, missile_time=i * t, x=x, y=y
            )
            )


        # Launch a missile at the specified coordinates and time
        response = stub.LaunchMissile(
            battlefield_pb2.BattlefieldMissileRequest(
                x=x, y=y, missile_type=missile_type, missile_time=i * t  # Use i * t as missile time
            )
        )

        print("Iteration " + str(i) + ":")


        # If a commander is present and a missile is approaching, print the notification
        if flag == 1:
            print(f"\n{BLUE}{missile_approaching_response}{WHITE}")

        # Retrieve the commander's ID again
        comm_response = stub.FindCommander(battlefield_pb2.Empty())

        # Call the WasHit RPC to check if the commander was hit
        wasHit_response = stub.WasHit(battlefield_pb2.WasHitRequest(soldier_id=comm_response.id))

        # Check if the commander is hit and there are still living soldiers
        if comm_response.id == -1 and casualities != M:
            print("Commander Died. Re-electing commander")
            stub.MakeCommander(battlefield_pb2.Empty())

        # Retrieve the commander's ID once more
        comm_response = stub.FindCommander(battlefield_pb2.Empty())

        # Get updated soldier information after the missile launch
        updated_layout_response = stub.GetInitialLayout(battlefield_pb2.GetInitialLayoutRequest())
        updated_layout = updated_layout_response.battlefield_layout
        soldiers = updated_layout_response.soldiers

        print()
        print(f"{YELLOW}Status after missile launch{WHITE}")
        # Print the updated battlefield layout
        printLayout(updated_layout, comm_response.id, max_length)
        print(f"\n{YELLOW}{response.message}{WHITE}")


        #get all alive and dead soldiers
        status_all_response = stub.StatusAll(battlefield_pb2.Empty())
        alive_soldiers = status_all_response.alive_soldiers 
        dead_soldiers = status_all_response.dead_soldiers

        print(f"{YELLOW}\nSoldiers Status:- {WHITE}")

        if alive_soldiers:
            print(f"{YELLOW}Alive Soldiers: {WHITE}")
            print_soldier_info(status_all_response.alive_soldiers)

        if dead_soldiers:
            print(f"{YELLOW}Dead Soldiers: {WHITE}")
            print_soldier_info(status_all_response.dead_soldiers)

        casualities=len(dead_soldiers)

        if i==num_iterations:
            #Dont want to wait after all missiles have been launched 
            break

        time.sleep(t)

    if casualities < (0.5 * M):
        print(f"\n\n {YELLOW}BATTLE WON{WHITE}")
    else:
        print(f"\n\n{YELLOW}BATTLE LOST{WHITE}")


if __name__ == '__main__':
    main()
