import grpc
import battlefield_pb2
import battlefield_pb2_grpc
from concurrent import futures
import random

# Defining the implementation of the Battlefield 
class BattlefieldServicer(battlefield_pb2_grpc.BattlefieldServiceServicer):
    def __init__(self):
        # Initialize class variables
        self.N = 0
        self.M = 0
        self.battlefield = []
        self.soldiers = []
        self.dead_soldiers = []
        self.positions = []
        self.eliminated_soldiers = []

    # Initializing the battlefield based on the input size
    def InitializeBattlefield(self, request, context):
        self.N = request.n
        self.M = request.m

        # Initialize the battlefield with '_' characters(A NxN matrix will be created)
        self.battlefield = [['_' for _ in range(self.N)] for _ in range(self.N)]

        """During the creation of the battlefield, there should be no existing soldiers or dead soldiers. 
        Therefore, we clear the soldiers and dead_soldiers lists to ensure that any previous data is flushed out """
        self.soldiers = []
        self.dead_soldiers = []


        response = battlefield_pb2.InitializeResponse(
            battlefield_layout=self.get_layout(),
            soldiers=[]
        )
        return response


    # Retrieve the layout of the battlefield(whenever it is called from client it returns the battlefield layout and soldiers information)
    def GetInitialLayout(self, request, context):
        return battlefield_pb2.GetInitialLayoutResponse(
            battlefield_layout=self.get_layout(),
            soldiers=self.soldiers
        )


    # Elect a random soldier as the commander
    def MakeCommander(self, request, context):

        #If all soldiers are dead we cant make a commander so we will simply return
        if not self.soldiers:
            return battlefield_pb2.Empty()

        # Select a random soldier from the list
        random_soldier = random.choice(self.soldiers)

        # Change the selected soldier's is_commander attribute
        random_soldier.is_commander = True
        commander_id = random_soldier.id

        return battlefield_pb2.CommanderId(id=commander_id)

    
    # Find the current commander
    def FindCommander(self, request, context):
        for soldier in self.soldiers:
            if soldier.is_commander and soldier.is_alive:
                return battlefield_pb2.CommanderId(id=soldier.id)
        return battlefield_pb2.CommanderId(id=-1)  # Return -1 if no commander is found

    # Add a soldier to the battlefield
    def AddSoldier(self, request, context):
        soldier = request.soldier

        #checking the necessary conditions(Even though we make sure on the client side that all soldiers have diff x,y)
        if (
            0 <= soldier.x < self.N
            and 0 <= soldier.y < self.N
            and self.battlefield[soldier.x][soldier.y] == '_'
        ):
            # Add the soldier to the battlefield
            self.battlefield[soldier.x][soldier.y] = str(soldier.id)
            self.soldiers.append(soldier)
            response = battlefield_pb2.AddSoldierResponse(message=f"Soldier {soldier.id} added to the battlefield.")
        else:
            response = battlefield_pb2.AddSoldierResponse(message=f"Invalid position for Soldier {soldier.id}. Soldier not added.")

        return response

    
    # Generate the current layout of the battlefield as a string(used by GetInitialLayout, InitializeBattlefield)
    def get_layout(self):
        return '\n'.join([','.join(row) for row in self.battlefield])  # Use a comma as the delimiter

    
    # Get the status of all soldiers (alive and dead)
    def StatusAll(self, request, context):
        # Send information about both active and dead soldiers
        response = battlefield_pb2.StatusAllResponse(
            alive_soldiers=self.soldiers,
            dead_soldiers=self.dead_soldiers
        )
        return response

    # Handle the incoming missile and calculate its impact
    def MissileApproaching(self, request, context):
        """
        Missile approaching function is called by commander, it sends of broadcasts information about the positions where missile impacts
        We dont reach the else part because we only call this when we have a commander(condition check on client side)

        """
        soldier_id = request.soldier_id
        missile_type = request.missile_type
        missile_time = request.missile_time
        missile_x = request.x
        missile_y = request.y

        #clearing the positions otherwise it may have previous iteration positions
        self.positions = []
        self.positions = self.find_impact_positions(missile_x, missile_y, missile_type)
        self.eliminated_soldiers = []

        if soldier_id != -1:
            commander = None

            # Find the commander with the matching id and is_commander=True
            for soldier in self.soldiers:
                if soldier.id == soldier_id and soldier.is_commander:
                    commander = soldier
                    break

            if commander:
                response = battlefield_pb2.BroadcastResponse(
                    message=f"Missile m{missile_type} approaching at ({missile_x}, {missile_y}) on positions {self.positions}."
                )
            else:
                # Handle the case when soldier_id is not a commander
                response = battlefield_pb2.BroadcastResponse(
                    message=f"Unauthorized soldier {soldier_id} attempted to control missile."
                )
        else:
            # Handle the case when soldier_id is -1 (no commander)
            response = battlefield_pb2.BroadcastResponse(
                message="All soldiers are dead."
            )

        return response

    # Move soldiers to safe positions to avoid missile impact
    def take_shelter(self, soldier, positions, eliminated_soldiers):
        for other_soldier in self.soldiers:
            if (other_soldier.x, other_soldier.y) in positions and other_soldier.Si > 0:
                flag = False
                curr_x = other_soldier.x
                curr_y = other_soldier.y

                #a soldier can move from -si to +si blocks(It can reach anywhere within the range so 2 for loops)
                for dx in range(-other_soldier.Si, other_soldier.Si + 1):
                    for dy in range(-other_soldier.Si, other_soldier.Si + 1):
                        new_x = curr_x + dx
                        new_y = curr_y + dy

                        if (
                            0 <= new_x < self.N
                            and 0 <= new_y < self.N
                            and (new_x, new_y) not in positions
                            and self.battlefield[new_x][new_y] == '_'
                        ):
                            # Clear the soldier's current position in the battlefield
                            self.battlefield[other_soldier.x][other_soldier.y] = '_'

                            # Update the soldier's new position
                            other_soldier.x = new_x
                            other_soldier.y = new_y

                            # Update the battlefield with the soldier's new position
                            self.battlefield[new_x][new_y] = str(other_soldier.id)

                            flag = True
                            break
                    if flag:
                        break

    # Handle missile launch and its impact on the battlefield
    def LaunchMissile(self, request, context):
        """
        Once commander has broadcasted the information about the missile..
        In this function we will see what happens when missile is launched.
        soldiers will move to safe positions because they have been alerted. 
        Commander only interacts with alive soldiers bcoz soldiers list only have soldiers that are alive
        We then loop over the impact areas and find if there are any soldier ids in that impact range and add it to eliminated_soldiers
        """
        x = request.x
        y = request.y
        missile_type = request.missile_type
        missile_time = request.missile_time

        # Create a list to track eliminated soldiers
        self.eliminated_soldiers = []

        # Clear all 'X' marks in the battlefield(previous iteration have added 'X' so we will remove and replace it with this iterations missile impact range) 
        for i in range(self.N):
            for j in range(self.N):
                if self.battlefield[i][j] == 'X':
                    self.battlefield[i][j] = '_'

        # Move soldiers to safe positions
        for soldier in self.soldiers:
            self.take_shelter(soldier, self.positions, self.eliminated_soldiers)

        self.positions = []
        self.positions = self.find_impact_positions(x, y, missile_type)

        for (row, col) in self.positions:
            if self.battlefield[row][col] != '_':
                soldier_id = int(self.battlefield[row][col])  # Get the soldier's ID
                eliminated_soldier = None

                # Find the soldier in self.soldiers using their ID
                for soldier in self.soldiers:
                    if soldier.id == soldier_id:
                        if soldier.is_commander:
                            # Handle the case where the eliminated soldier is the commander
                            # Update is_alive and is_commander
                            soldier.is_alive = False
                            soldier.is_commander = False
                        else:
                            # Handle the case for non-commander eliminated soldiers
                            soldier.is_alive = False

                        # Add the eliminated soldier to the list
                        eliminated_soldier = soldier
                        break

                if eliminated_soldier:
                    self.eliminated_soldiers.append(eliminated_soldier)
                    self.dead_soldiers.append(eliminated_soldier)
                    self.soldiers.remove(eliminated_soldier)

            self.battlefield[row][col] = 'X'  # Mark the position with 'X'

        if self.eliminated_soldiers:
            eliminated_soldier_ids = [int(soldier.id) for soldier in self.eliminated_soldiers]
            eliminated_soldier_ids.sort()
            eliminated_soldiers_str = ', '.join(map(str, eliminated_soldier_ids))
            return battlefield_pb2.MissileResponse(
                message=f"Missile m{missile_type} hit at ({x}, {y}). Soldiers {eliminated_soldiers_str} were eliminated!"
            )

        return battlefield_pb2.MissileResponse(message=f"Missile m{missile_type} missed at ({x}, {y}). No soldier was killed in this iteration.")

    

    """ Find positions impacted by a missile based on its type and coordinates
    (we dont want redundant positions so have used set and have sorted the positions)"""
    def find_impact_positions(self, x, y, missile_type):
        positions = []
        for iteration in range(0, missile_type):
            for row in range(x - iteration, x + iteration + 1):
                for col in range(y - iteration, y + iteration + 1):
                    if 0 <= row <= self.N - 1 and 0 <= col <= self.N - 1:
                        positions.append((row, col))

        # Convert the list to a set to automatically remove duplicates
        unique_positions = set(positions)

        # Convert the set back to a list if needed
        unique_positions_list = list(unique_positions)

        # Sort the positions in ascending order
        sorted_positions = sorted(unique_positions_list, key=lambda pos: (pos[0], pos[1]))

        return sorted_positions

    
    # Check if a soldier was hit by a missile
    def WasHit(self, request, context):
        soldier_id = request.soldier_id

        # Initialize hit to False
        hit = False

        # Check if soldier_id is in eliminated_soldiers
        for soldier in self.eliminated_soldiers:
            if soldier.id == soldier_id:
                hit = True
                break

        response = battlefield_pb2.WasHitResponse(hit=hit)

        return response


def serve():
    # Create a gRPC server with a thread pool executor that can handle up to 10 worker threads.
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Add the BattlefieldServicer implementation to the server, allowing it to handle gRPC service requests.
    battlefield_pb2_grpc.add_BattlefieldServiceServicer_to_server(BattlefieldServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Server started...")
    server.wait_for_termination()

# Main function to start the server
if __name__ == '__main__':
    serve()
