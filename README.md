# AOS_Assignment_first

# Group Details 
Chahat Kalra   2022H1120278P 
Soumya Agrawal 2022H1120289P

# Prerequisites
-Python 3.x
-grpc Library

# Setup
1.Clone the repository to your local machine

'''
git clone https://github.com/SoumyaAgrawal1/AOS_Assignment_first.git
'''

2.Install the required libraries

'''
pip install -r requirements.txt
'''
# Running the Simulation
- 1.Run this command

'''
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. battlefield.proto
'''

This generates battlefield_pb2.py and battlefield_pb2_grpc.py files.

2.Start the RPC Server on the same machine

'''
python server.py
'''

2.Start the RPC Client on the same machine

'''
python client.py
'''
