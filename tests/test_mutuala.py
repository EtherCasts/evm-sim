from sim import Key, Simulator, compile_serpent
from pyethereum.utils import coerce_to_bytes

import pytest

def account_balance_offset(address):
    return coerce_to_bytes(int(address, 16) + 2**161)


class TestMutuala(object):

    ALICE = Key('cow')
    BOB = Key('cat')
    CHARLIE = Key('car')

    @classmethod
    def setup_class(cls):
        cls.code = compile_serpent('examples/mutuala.se')
        cls.sim = Simulator({cls.ALICE.address: 10**18,
                             cls.BOB.address: 10**18})

    def setup_method(self, method):
        self.sim.reset()
        self.contract = self.sim.load_contract(self.ALICE, self.code)

    def test_creation(self):
        assert self.sim.get_storage_data(self.contract, account_balance_offset(self.ALICE.address)) == 10**12
        assert self.sim.get_storage_data(self.contract, coerce_to_bytes(2**160-1)) == 1
        assert self.sim.get_storage_data(self.contract, coerce_to_bytes(2**160)) == int(self.ALICE.address, 16)

    def test_alice_balance(self):
        ans = self.sim.tx(self.ALICE, self.contract, 0, ["balance", self.ALICE.address])
        assert ans == [10**12]

    def test_alice_pay_to_bob(self):
        from pprint import pprint
        pprint(self.sim.genesis)
        ans = self.sim.tx(self.ALICE, self.contract, 0, ["pay", self.BOB.address, 1000])
        assert ans == [1]
        assert self.sim.get_storage_data(self.contract, account_balance_offset(self.ALICE.address)) == 999999999000
        assert self.sim.get_storage_data(self.contract, account_balance_offset(self.BOB.address)) == 1000

        # new account gets registered
        assert self.sim.get_storage_data(self.contract, coerce_to_bytes(2**160-1)) == 2
        assert self.sim.get_storage_data(self.contract, coerce_to_bytes(2**160)) == int(self.ALICE.address, 16)
        assert self.sim.get_storage_data(self.contract, coerce_to_bytes(2**160+1)) == int(self.BOB.address, 16)

        # make another payment
        ans = self.sim.tx(self.ALICE, self.contract, 0, ["pay", self.BOB.address, 1000])
        assert ans == [1]
        assert self.sim.get_storage_data(self.contract, account_balance_offset(self.ALICE.address)) == 999999998000
        assert self.sim.get_storage_data(self.contract, account_balance_offset(self.BOB.address)) == 2000

        # new account gets registered only once
        assert self.sim.get_storage_data(self.contract, coerce_to_bytes(2**160-1)) == 2

    def test_bob_to_charlie_invalid(self):
        ans = self.sim.tx(self.BOB, self.contract, 0, ["pay", self.CHARLIE.address, 1000])
        assert ans[0] == 0
        assert coerce_to_bytes(ans[1]) == "insufficient balance"
        assert self.sim.get_storage_data(self.contract, account_balance_offset(self.ALICE.address)) == 10**12
        assert self.sim.get_storage_data(self.contract, account_balance_offset(self.BOB.address)) == 0
        assert self.sim.get_storage_data(self.contract, account_balance_offset(self.CHARLIE.address)) == 0

    def test_alice_to_bob_to_charlie_valid(self):
        ans = self.sim.tx(self.ALICE, self.contract, 0, ["pay", self.BOB.address, 1000])
        assert ans == [1]

        ans = self.sim.tx(self.BOB, self.contract, 0, ["pay", self.CHARLIE.address, 250])
        assert ans == [1]

        assert self.sim.get_storage_data(self.contract, account_balance_offset(self.ALICE.address)) == 999999999000
        assert self.sim.get_storage_data(self.contract, account_balance_offset(self.BOB.address)) == 750
        assert self.sim.get_storage_data(self.contract, account_balance_offset(self.CHARLIE.address)) == 250
