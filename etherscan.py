import os
import requests
import json
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
        response =  Response(requests.get(self.endpoint, params=params))
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
            return (self.wei*-1)+(self.gasCost*-1)
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

    def __str__(self):
        return self.address

    def balance(self):
        response = self.request(params={
            'module': 'account',
            'action': 'balance',
            'address': self.address,
            'tag': 'latest',
        })
        if response.ok:
            return ether(response['result'])

    def __eq__(self, other):
        return self.address.lower() == other.address.lower()

    def __ne__(self, other):
        return self.address.lower() != other.address.lower()

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--addr', required=True)
    return parser.parse_args()

def main():
    load_dotenv()
    args = parse_args()

    account = Account(args.addr)
    transactions  = list(account.transactions.normal())
    transactions += list(account.transactions.internal())
    transactions = sorted(transactions, key=lambda x: x['timeStamp'])

    balance = 0
    max = 0
    for transaction in transactions:
        if transaction.balance != 0:
            balance += transaction.balance
            print(f'{transaction} balance: {ether(balance):.3f}')
            if max < balance:
                max = balance
    print(f'balance: {account.balance():.3f}')
    print(f'max: {ether(max):.3f}')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
