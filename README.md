## Blockchain

Blockchains are a big word lately, especially related to all the cryptocurrency buzz that is going up and down the financial markets. Given that blockchains really are just chains of blocks, why are they so relevant and why so many different applications are trying to find a use for them?
The reason the blockchain is so popular can be summarized in two words: *hash* and *replication*. These two properties of the chain are the main reason the chain itself is described as immutable and therefore secure to host financial transactions (although it could host any kind of data).

The code is taken from the [Learn Blockchains by Building One](https://hackernoon.com/learn-blockchains-by-building-one-117428612f46) article and slightly adapted. I felt the code was really good but I needed some more details to understand what was going on, so I used it and added my own comments to the inner workings of the blockchain. Thanks to [Daniel van Flymen](https://hackernoon.com/@vanflymen) for the original writing!

### Hashes
            
A **hash** is a digest of whatever input has been passed to the hashing function. The output is virtually unique: it is possible that two different inputs have the same hash (this is called a collision), but the probability of this happening is really, really low. Usually hashes have a fixed length no matter the size of the input (for example, SHA256 always has an output of 256 bits) and have the nice property of resulting in radically different outputs even if the inputs change only slightly, making it easier to see that something is different.
Knowing the hash of a message allows to check its integrity: it is enough to compute the hash of the message that you recevied and compare it to the already known hash, if there is any difference something has happened to the message in the meantime.<br> Every block of the blockchain contains the hash of the previous block: it is easy to see how this creates a recursion, with the last block containing the digest of the previous block contianing the digest of the previous block contianing... up to the *genesis* block. This means that if one block is modified and therefore his hash changes, the entire chain after that block has to be updated to reflect the changes, otherwise it will be clear that something is wrong somewhere.

```python
def hash(self, block):
    block_string = json.dumps(block, sort_keys=True).encode()
    return hashlib.sha256(block_string).hexdigest()
```

### Replication
            
However, hashes alone are not enough to guarantee that no modifications happen along the blockchain. This is where **replication** comes into the game: all actors taking part in adding blocks to the chain are expected to keep a copy of the chain itself and to keep it updated. At least half+1 of the participants (meaning the majority) have to have the same chain for it to be valid.
In terms of trying to maliciously modify a block that is already stored in the chain, this means that not only all the following blocks have to be modified with updated hashes for that chain, but that the same operations have to be done to at least half of the other participants, so that the modified chain becomes majority.
The more widespread the blockchain system is adopted, the more difficult it becomes to tamper it successfully.
        
### Blocks

Each block can contain whatever data you want, but in our case it will be transactions. To be part of the chain a block needs the following elements:

- **Index:** a unique identifier, ordered and ascending
- **Timestamp:** a Unix time timestamp recording when the block was created
- **List of transactions:** all the transactions to be stored in that block, with source, destination and amount
- **Proof of work:** verifiable mining value
- **Hash:** the hash of the previous block

```python
def new_block(self, proof, prev = None):
    block = {
        'index': len(self.chain) + 1,
        'timestamp': time(),
        'transactions': self.current_transactions,
        'proof': proof,
        'prev': prev or slef.hash(self.chain[-1])
    }

    self.current_transactions = []
    self.chain.append(block)
    return block
    
 def last_block(self):
    return self.chain[-1]
```

### Transactions
            
Transactions are dictionaries containing their own source and destination address, and total to be moved between the two. A new transaction is created by appending it to the list of current transactions of the block and returning the index of the current block (meaning the index of the last block plus 1).
            
```python
def new_transaction(self, src, dst, tot):
    self.current_transaction.append({
        'src': src,
        'dst': dst,
        'tot': tot
    })

    return self.last_block['index'] + 1
```

### Proof of Work

New blocks can't be inserted in the chain for free, but they first have to be *mined*. This means solving a difficult problem and using the result as a proof of work: this problem, called *hashcash*, is difficult to solve but the solution is easy to verify. This means that after somebody solved the problem, all the nodes hosting the blockchain can verify the block before adding it to the chain.
Our proof of work will be the following:

> Find a number p that when hashed with the previous block returns a hash with 4 leading 0s.

To find that number we are iterating over the last proof and a new proof value, and checking whether their hashed value satisfies the requiement.
            
```python
def pow(self, lastpow):
    pow = 0
    found = False
    while !self.valid_pow(lastpow, pow):
        pow += 1

    return pow

def valid_pow(lastpow, pow):
    next = f'{lastpow}{pow}'.encode()
    next_hash = hashlib.sha256(next).hexdigest()
    return next_hash[:4] == '0000'
```

### Nodes handling
            
Blockchains work in distributed networks made of nodes, where each node is storing a copy of the chain and working on it. We will be running server instances where each server corresponds to a node, and to do this we use the [Python Flask Framework](http://flask.pocoo.org/). We start by creating the application and declaring three routes: */mine* to mine a new block, */transactions/new* to append a new transaction to a block, and */chain* to return the full chain.
We also set the server to start running when the program is executed, and to listen on port 5000. This means that we can interact with it by sending the proper requests to localhost:500/xxx where xxx is one of the defined routes.
            
```python
app = Flask(__name__)
node_id = str(uuid4()).replace('-','')
blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    ...

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    ...

@app.route('/chain', methods=['GET'])
def chain():
    ...

if __name == '__main__':
    app.run(host='0.0.0.0', port=5000)
```
Given that the whole point of a distributed system is that it runs on multiple nodes, we need to be able to let many servers run and store the blockchain simultaneously, without creating conflicts and while staying up to date. Each server will keep a list of the other active servers, and the blockchain itself will do that too.
We modify the Blockchain class by adding a set of nodes in the constructor, and a method to add new nodes by storing their address in the set (using the *set* data structure ensures that every element will be stored exactly once).
            
```python
def __init__(self):
    ...
    self.nodes = set()
    ...
    
def register_node(self, address):
    url = urlparse(address)
    self.nodes.add(url.netloc)
```

### Consensus

To ensure that all nodes are storing the same chain, they all need to reach consensus. To do this, we declare the longest valid chain as the only valid one, and all nodes that are holding a different shorter version should update. Our blockchain class provides two nice methods that help checking whether a chain is valid and resolves conflicts if a node has a different version of the chain. These two actions will be invoked through server endpoints.
The validation is done by going over each block of the chain, checking that its hashing and its proof of work are correct.

```python
def validation(self, chain):
    last = chain[0]
    index = 1

    while index &lt; len(chain):
        block = chain[index]

        if block['prev'] != self.hash(last):
            return False

        if not self.valid_pow(last):
            return False

        last = block
        index += 1

    return True
 ```
    
The conflict resolution for a node is done by going through all of the other nodes and sending a request to their /chain endpoint. The response will contain the chain of the interrogated node, and its length. In case the returned chain is longer than the one the node is holding, the local values are updated. In the end, the maximum length chain will be the one remaining and it will be stored as local one.
            
```python
def resolve(self):
    neighbors = self.nodes
    new_chain = None
    max_len = len(self.chain)

    for node in neighbors:
        response = requests.get(f'http://{node}/chain')

        if response.status_code == 200:
            length = response.json()['length']
            chain = response.json()['chain']

            if length &gt; max_len and self.validation(chain):
                max_len = length
                new_chain = chain

    if new_chain:
        self.chain = new_chain
        return True

    return False
```

#### Endpoint: /mine
            
When a user requests to mine a new block, the server will calculate the proof of work and reward itself by adding a transaction that gives it 1 coin. Then it creates the new block with the newly found proof of work and appends it to the chain.

```python
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
    
    return jsonigy(response), 200
```

#### Endpoint: /transactions/new
            
With this request the user is sending the request with a json object with the following structure:

>{"sender": "xxx",
> "recipient": "yyy",
> "amount": 111}
            
The server will read these values and check that they correspond to the requried ones (sender, recipient, amount). If they do not, the server will send back an HTTP status 400, corresponding to a client side "bad request". If the parameters fulfill the requirements, a new transaction is inserted in the blockchain and its index is sent back to the user together with the 201 status, corresponding to "created".
            
```python
@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400
    
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
    response = {'message': f'Transaction registered in block {index}'}
    return jsonify(response), 201
```

#### Endpoint: /chain

With this request the user is presented with a status 200, corresponding to "success" and a response containing the current blockchain and its length.
            
```python
@app.route('/chain', methods=['GET'])
def chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200
```

#### Endpoint /node/register
            
To register nodes the user can send a POST request containing a list of nodes in the format ```{"nodes": ["http//192.168.0.0:8080"]}``` and the server will put it in its set.
            
```python
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
```

#### Endpoint /nodes/consensus
            
Whenever a user wants to check whether its node is holding the authoritative chain and resolve the conflict if the node has a non authoritative copy, it can ask for the resolve() method to do its work.

```python
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
```
