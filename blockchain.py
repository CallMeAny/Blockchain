# Original article: https://hackernoon.com/learn-blockchains-by-building-one-117428612f46
# Original source: https://github.com/dvf/blockchain

import time
import json
import hashlib
import requests
from flask import Flask, jsonify, request
from uuid import uuid4
from urllib.parse import urlparse

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.new_block(proof = 100, phash = 1)
        self.nodes = set()
        
    def register(self, address):
        url = urlparse(address)
        self.nodes.add(url.netloc)
        
    def validation(self, chain):
        last = chain[0]
        index = 1
        
        while index < len(chain):
            block = chain[index]
            
            if block['prev'] != self.hash(last):
                return False
            
            if not self.valid_pow(last['proof'], block['proof']):
                return False
            
            last = block
            index += 1
        
        return True
    
    def resolve(self):
        neighbors = self.nodes
        new_chain = None
        max_len = len(self.chain)
        
        for node in neighbors:
            response = requests.get(f'http://{node}/chain')
            
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                
                if length > max_len and self.validation(chain):
                    max_len = length
                    new_chain = chain
                    
        if new_chain:
            self.chain = new_chain
            return True

        return False
    
    
    def new_block(self, proof, phash = None):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time.time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'prev': phash or self.hash(self.chain[-1])
        }
        
        self.current_transactions = []
        self.chain.append(block)
        return block
    
    def new_transaction(self, src, dst, tot):
        self.current_transactions.append({
            'src': src,
            'dst': dst,
            'tot': tot
        })
        
        return self.last_block['index'] + 1
    
    @property
    def last_block(self):
        return self.chain[-1]
    
    def hash(self, block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
    
    def pow(self, lastpow):
        pow = 0
        found = False
        while self.valid_pow(lastpow, pow) is False:
            pow += 1
            
        return pow
    
    def valid_pow(self, lastpow, pow):
        next = f'{lastpow}{pow}'.encode()
        next_hash = hashlib.sha256(next).hexdigest()
        return next_hash[:4] == '0000'
    
app = Flask(__name__)
node_id = str(uuid4()).replace('-','')
blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.pow(last_proof)
    blockchain.new_transaction(
        src='0', #use value instead of node_id to identify pow award
        dst=node_id,
        tot=1
    )
    
    prev_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, prev_hash)
    
    response = {
        'message': 'New block forged',
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'prev_hash': block['prev']
    }
    
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400
    
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
    response = {'message': f'Transaction registered in block {index}'}
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register():
    values = request.get_json()
    nodes = values.get('nodes')
    if nodes is None:
        return "Wrong list of nodes", 400
    
    for node in nodes:
        blockchain.register(node)
        
    response = {
        'message': 'New node registered',
        'total': list(blockchain.nodes)
    }
    return jsonify(response), 201
    
@app.route('/nodes/consensus', methods=['GET'])
def consensus():
    consensus = blockchain.resolve()
    if consensus:
        response = {
            'message': 'Updated chain',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Authoritative chain',
            'chain': blockchain.chain
        }
        
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
