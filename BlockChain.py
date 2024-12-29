import hashlib, json, random, logging, socket, threading, copy
from datetime import datetime
import time
import tkinter as tk
from tkinter import messagebox

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Create the genesis block
def create_genesis_block():
    return {
        'index': 0,
        'timestamp': str(datetime.now()),
        'transactions': [],
        'previous_hash': '0',
        'hash': 'genesis_block_hash'
    }

# Blockchain Application Class
class BlockchainApp:
    def __init__(self, root, node_port=5000, tracker_ip="localhost", tracker_port=6000):
        self.root = root
        self.root.title("Blockchain Application")
        self.chain = [create_genesis_block()]
        self.node = Node('localhost', node_port, self.chain, tracker_ip, tracker_port)
        self.difficulty = 3
        self.block_size_limit = 5
        self.miner = "Alice"
        self.PARTICIPANTS = []
        self.peers = []

        self.create_widgets()

    def create_widgets(self):
        self.dashboard_frame = tk.Frame(self.root, bg='#f0f0f0', bd=5)
        self.dashboard_frame.pack(pady=20, padx=20, fill='x')

        self.block_count_label = tk.Label(self.dashboard_frame, text="Block Count: 0", font=("Arial", 12), bg='#f0f0f0')
        self.block_count_label.grid(row=0, column=0, padx=20)

        self.txn_count_label = tk.Label(self.dashboard_frame, text="Transaction Count: 0", font=("Arial", 12), bg='#f0f0f0')
        self.txn_count_label.grid(row=0, column=1, padx=20)

        self.difficulty_label = tk.Label(self.dashboard_frame, text=f"Difficulty: {self.difficulty}", font=("Arial", 12), bg='#f0f0f0')
        self.difficulty_label.grid(row=0, column=2, padx=20)

        self.participant_frame = tk.Frame(self.root, bg='#f7f7f7', bd=5)
        self.participant_frame.pack(pady=20, padx=20, fill='x')

        self.add_participant_label = tk.Label(self.participant_frame, text="Add Participant", font=("Arial", 14, 'bold'), bg='#f7f7f7')
        self.add_participant_label.pack(pady=10)

        self.participant_name_entry = tk.Entry(self.participant_frame, font=("Arial", 12), bd=2, relief="solid", width=30)
        self.participant_name_entry.pack(pady=10)

        self.add_participant_button = tk.Button(self.participant_frame, text="Add Participant", font=("Arial", 12), bg="#4CAF50", fg="white", command=self.add_participant, relief="raised", width=20)
        self.add_participant_button.pack(pady=10)

        self.operations_frame = tk.Frame(self.root, bg='#f7f7f7', bd=5)
        self.operations_frame.pack(pady=20, padx=20, fill='x')

        self.create_txn_button = tk.Button(self.operations_frame, text="Create Transaction", font=("Arial", 12), bg="#008CBA", fg="white", command=self.create_transaction, relief="raised", width=20)
        self.create_txn_button.pack(pady=10)

        self.mine_block_button = tk.Button(self.operations_frame, text="Mine Block", font=("Arial", 12), bg="#ff9800", fg="white", command=self.mine_block, relief="raised", width=20)
        self.mine_block_button.pack(pady=10)

        self.send_txn_button = tk.Button(self.operations_frame, text="Send Transaction", font=("Arial", 12), bg="#f44336", fg="white", command=self.send_transaction, relief="raised", width=20)
        self.send_txn_button.pack(pady=10)

        self.show_chain_frame = tk.Frame(self.root, bg='#f7f7f7', bd=5)
        self.show_chain_frame.pack(pady=20, padx=20, fill='x')

        self.show_chain_button = tk.Button(self.show_chain_frame, text="Show Blockchain", font=("Arial", 12), bg="#9C27B0", fg="white", command=self.show_blockchain, relief="raised", width=20)
        self.show_chain_button.pack(pady=10)

    def add_participant(self):
        participant_name = self.participant_name_entry.get()
        if participant_name and participant_name not in self.PARTICIPANTS:
            self.PARTICIPANTS.append(participant_name)
            messagebox.showinfo("Success", f"{participant_name} added to the blockchain.")
        else:
            messagebox.showwarning("Error", "Participant already exists or name is empty.")

    def create_transaction(self):
        try:
            txn = makeTransaction()
            messagebox.showinfo("Transaction Created", f"Transaction: {txn}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def mine_block(self):
        transactions = self.node.txnBuffer[:self.block_size_limit]
        if not transactions:
            messagebox.showwarning("No Transactions", "There are no transactions to include in the block.")
            return
        
        block = makeBlock(transactions, self.node.chain, self.difficulty)
        self.node.chain.append(block)
        self.node.txnBuffer = self.node.txnBuffer[self.block_size_limit:]

        self.block_count_label.config(text=f"Block Count: {len(self.node.chain)}")
        self.txn_count_label.config(text=f"Transaction Count: {sum(len(block['transactions']) for block in self.node.chain)}")
        
        messagebox.showinfo("Block Mined", f"New block mined: {block['hash']}")

    def send_transaction(self):
        txn = makeTransaction()
        self.node.txnBuffer.append(txn)
        self.broadcast_transaction(txn)
        messagebox.showinfo("Transaction Sent", f"Transaction: {txn} sent.")

    def show_blockchain(self):
        blockchain_info = "\n".join([str(block) for block in self.node.chain])
        messagebox.showinfo("Blockchain", blockchain_info)

    def broadcast_transaction(self, txn):
        for peer in self.node.peers:
            try:
                peer.send(json.dumps({'type': 'new_transaction', 'data': txn}).encode())
            except Exception as e:
                logger.error(f"Failed to broadcast transaction to peer {peer}: {e}")

    def connect_to_peer(self, peer_address):
        try:
            peer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer.connect(peer_address)
            self.node.peers.append(peer)
            logger.info(f"Connected to peer at {peer_address}")
        except Exception as e:
            logger.error(f"Failed to connect to peer {peer_address}: {e}")

    def discover_peers(self):
        try:
            tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tracker_socket.connect((self.node.tracker_ip, self.node.tracker_port))
            tracker_socket.send(b'GET_PEERS')
            peers = tracker_socket.recv(1024).decode().splitlines()
            for peer in peers:
                host, port = peer.split(':')
                self.connect_to_peer((host, int(port)))
        except Exception as e:
            logger.error(f"Error discovering peers: {e}")

# Node Class for P2P network
class Node:
    def __init__(self, host, port, chain, tracker_ip, tracker_port):
        self.host = host
        self.port = port
        self.peers = []
        self.chain = copy.deepcopy(chain)
        self.txnBuffer = []
        self.state = {}
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port

    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.host, self.port))
        server.listen(5)
        logger.info(f"Node running on {self.host}:{self.port}")

        while True:
            conn, addr = server.accept()
            threading.Thread(target=self.handle_client, args=(conn, addr)).start()

    def handle_client(self, conn, addr):
        logger.info(f"Connection established with {addr}")
        data = conn.recv(1024).decode()
        if data:
            self.process_message(json.loads(data))
        conn.close()

    def process_message(self, message):
        if message['type'] == 'new_block':
            self.handle_new_block(message['data'])
        elif message['type'] == 'new_transaction':
            self.handle_new_transaction(message['data'])

    def handle_new_block(self, block):
        try:
            self.state = checkBlockValidity(block, self.chain[-1], self.state)
            self.chain.append(block)
            logger.info(f"New block added to the chain from peer.")
        except Exception as e:
            logger.error(f"Invalid block: {e}")

    def handle_new_transaction(self, txn):
        self.txnBuffer.append(txn)
        logger.info(f"New transaction added: {txn}")

    def mine_block(self):
        transactions = self.txnBuffer[:5]
        if not transactions:
            logger.warning("No transactions to mine.")
            return
        new_block = makeBlock(transactions, self.chain, 3)
        self.chain.append(new_block)
        self.txnBuffer = self.txnBuffer[5:]

        for peer in self.peers:
            peer.send(json.dumps({'type': 'new_block', 'data': new_block}).encode())
        logger.info(f"Block mined: {new_block}")

# Helper Functions for Transaction and Block Creation
def makeTransaction():
    txn = {
        'sender': random.choice(['Alice', 'Bob', 'Charlie']),
        'receiver': random.choice(['Dave', 'Eve', 'Frank']),
        'amount': random.randint(1, 100)
    }
    return txn

def makeBlock(transactions, chain, difficulty):
    index = len(chain)
    timestamp = str(datetime.now())
    previous_hash = chain[-1]['hash']
    block_data = {
        'index': index,
        'timestamp': timestamp,
        'transactions': transactions,
        'previous_hash': previous_hash,
        'hash': hashlib.sha256(f'{index}{timestamp}{transactions}{previous_hash}'.encode()).hexdigest()
    }
    return block_data

def checkBlockValidity(block, previous_block, state):
    if block['previous_hash'] != previous_block['hash']:
        raise Exception("Invalid previous hash.")
    if not block['hash'].startswith('0' * state.get('difficulty', 3)):
        raise Exception("Block does not meet difficulty target.")
    return state

# Start the Tracker
def start_tracker():
    tracker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tracker.bind(('localhost', 6000))
    tracker.listen(5)
    logger.info("Tracker is running.")

    while True:
        conn, addr = tracker.accept()
        data = conn.recv(1024).decode()
        if data == 'GET_PEERS':
            peers = 'localhost:5000\nlocalhost:6001'  
            conn.send(peers.encode())
        conn.close()

# Start GUI and Node in Parallel
root = tk.Tk()
app = BlockchainApp(root)
node_thread = threading.Thread(target=app.node.start_server)
node_thread.daemon = True
node_thread.start()


tracker_thread = threading.Thread(target=start_tracker)
tracker_thread.daemon = True
tracker_thread.start()

root.mainloop()
