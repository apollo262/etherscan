import os
import requests
import json
import graphviz
from ether import ether
from dotenv import load_dotenv
from datetime import datetime
from argparse import ArgumentParser

class EtherscanAPI:
    def __init__(self):
        self.apikey = os.getenv('ETHERSCAN_API_KEY')
        self.endpoint = os.getenv('ETHERSCAN_API_ENDPOINT')

    def request(self, params):
        params.update({'apikey': self.apikey})
        response = Response(requests.get(self.endpoint, params=params))
        #print(json.dumps({'request': [self.endpoint, params], 'response': response}, indent=4))
        return response

class Response(dict):
    def __init__(self, response):
        super().__init__(json.loads(response.text))
        self.response = response
        setattr(self, 'status', int(self['status']))
        setattr(self, 'message', self['message'])

    @property
    def ok(self):
        return self.response.ok and self.status == 1 and self.message == 'OK'

class Transaction(dict):
    def __init__(self, transaction, account):
        super().__init__(transaction)
        self.account = account

        for key in ['gas', 'gasPrice', 'gasUsed']:
            value = 0 if not self.get(key) else int(self[key])
            setattr(self, key, value)

    def __str__(self):
        return '{} {} {} {:.3f}'.format(self.timestamp(), 'from' if self.rx else 'to  ', self.peer, ether(self.balance))

    @property
    def ether(self):
        return ether(self.value)

    @property
    def wei(self):
        return self.value

    @property
    def value(self):
        return int(self['value'])

    @property
    def account_from(self):
        return Account(self['from'])

    @property
    def account_to(self):
        return Account(self['to'])

    def timestamp(self):
        dt = datetime.fromtimestamp(int(self['timeStamp']))
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    @property
    def tx(self):
        return (self.account_from != self.account_to) and (self.account_from == self.account)

    @property
    def rx(self):
        return (self.account_from != self.account_to) and (self.account_to == self.account)

    @property
    def gasCost(self):
        return self.gasPrice*self.gasUsed

    @property
    def balance(self):
        if self.tx:
            return (self.wei*-1)-self.gasCost
        elif self.rx:
            return self.wei
        else:
            return 0

    @property
    def peer(self):
        if self.tx:
            return self.account_to
        elif self.rx:
            return self.account_from
        else:
            return self.account

class Transactions(EtherscanAPI):
    def __init__(self, account):
        super().__init__()
        self.account = account

    def default(self):
        return {
            'module': 'account',
            'address': self.account.address,
            'startblock': 0,
            'endblock': 99999999,
            'page': 1,
            'offset': 10000,
            'sort': 'asc',
        }

    def _request(self, params):
        response = self.request(params=params)
        if response.ok:
            for transaction in response['result']:
               yield Transaction(transaction, self.account)

    def normal(self):
        params = self.default()
        params.update({'action': 'txlist'})
        return self._request(params)

    def internal(self):
        params = self.default()
        params.update({'action': 'txlistinternal'})
        return self._request(params)

class Account(EtherscanAPI):
    def __init__(self, address):
        super().__init__()
        self.address = address
        self.transactions = Transactions(self)
        self.payments = Payments(self)
        self._balance = None

    def __str__(self):
        return self.address

    @property
    def balance(self):
        if self._balance is None:
            response = self.request(params={
                'module': 'account',
                'action': 'balance',
                'address': self.address,
                'tag': 'latest',
            })
            if response.ok:
                self._balance = int(response['result'])
        return self._balance

    def __eq__(self, other):
        return self.address.lower() == other.address.lower()

    def __ne__(self, other):
        return self.address.lower() != other.address.lower()

class AccountFactory:
    def __init__(self):
        self.accounts = {}

    def create(self, address):
        return self.accounts.setdefault(address, Account(address))
account_factory = AccountFactory()

class Payments:
    def __init__(self, account):
        self.account = account
        self.transactions = None
        self.peers = {}
        self.total = 0

    def initialize(self):
        self.transactions = get_transactions(self.account)
        for transaction in self.transactions:
            peer = self.peers.setdefault(transaction.peer.address, {
                'wei': 0, 'address': transaction.peer.address,
            })
            if transaction.tx:
                self.peers[transaction.peer.address]['wei'] += transaction.wei
            if transaction.rx:
                self.peers[transaction.peer.address]['wei'] -= transaction.wei

        for peer in self.peers.values():
            if peer['wei'] > 0:
                self.total += peer['wei']

        for peer in self.peers.values():
            if peer['wei'] > 0:
                peer['ratio'] = peer['wei']/self.total
            else:
                peer['ratio'] = 0

    def update_graph(self, graph, ratio=0.01):
        if self.transactions is None:
            self.initialize()

        for peer in self.peers.values():
            if peer['ratio'] > ratio:
                balance = self.account.balance
                print(f'{self.account.address}({ether(balance):,.0f})->{peer["address"]}({ether(peer["wei"]):,.0f}) {peer["ratio"]*100:.1f}%')
                graph.edge(
                    f'{self.account.address}\n({ether(balance):,.0f}ETH)',
                    f'{peer["address"]}\n({ether(account_factory.create(peer["address"]).balance):,.0f}ETH)',
                    label=f'{ether(peer["wei"]):,.0f}ETH ({peer["ratio"]*100:.1f}%)'
                )

    def get_peers(self, ratio=0.01):
        for addr in self.peers.keys():
            if self.peers[addr]['ratio'] > ratio:
                yield account_factory.create(addr)

def get_peers(account, graph, depth, ratio):
    if depth <= 0:
        return

    for peer in account.payments.get_peers(ratio):
        if peer.payments.transactions is None:
            peer.payments.update_graph(graph, ratio)
            get_peers(peer, graph, depth-1, ratio)

def get_transactions(account):
    transactions  = list(account.transactions.normal())
    transactions += list(account.transactions.internal())
    return sorted(transactions, key=lambda x: x['timeStamp'])

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--addr', '-a', required=True)
    parser.add_argument('--balance', '-b', action='store_true')
    parser.add_argument('--ratio', '-r', type=float, default=0.05)
    parser.add_argument('--depth', '-d', type=int, default=3)
    parser.add_argument('--format', '-f', default='pdf')
    return parser.parse_args()

def main():
    load_dotenv()
    args = parse_args()

    account = account_factory.create(args.addr)
    if args.balance:
        balance = 0
        for transaction in get_transactions(account):
            if transaction.balance != 0:
                balance += transaction.balance
                print(f'{transaction} balance: {ether(balance):.3f}')
        print(f'balance: {ether(account.balance):.3f}')
        assert(account.balance == balance)
    else:
        graph = graphviz.Digraph('unix', format=args.format, node_attr={'color': 'lightblue2', 'style': 'filled', 'shape': 'box'})
        graph.attr(size='6,6', rankdir='LR')
        account.payments.update_graph(graph, args.ratio)
        get_peers(account, graph, depth=args.depth, ratio=args.ratio)
        graph.render(f'{args.addr}_d{args.depth}_r{args.ratio}')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
