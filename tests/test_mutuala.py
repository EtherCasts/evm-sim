from sim import Key, Simulator, compile_serpent
from pyethereum.utils import coerce_to_bytes

import pytest


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

    def get_commons_balance(self):
        return self.sim.get_storage_data(self.contract, coerce_to_bytes(42))

    def get_account_balance(self, address):
        return self.sim.get_storage_data(self.contract, coerce_to_bytes(int(address, 16) + 2**161))

    def get_account_tax_credits(self, address):
        return self.sim.get_storage_data(self.contract, coerce_to_bytes(int(address, 16) + 2**161 + 2))

    def assert_account_list(self, expected_accounts):
        assert self.sim.get_storage_data(self.contract, coerce_to_bytes(2**160-1)) == len(expected_accounts)
        for idx, expected_account in enumerate(expected_accounts):
            assert self.sim.get_storage_data(self.contract, coerce_to_bytes(2**160 + idx)) == int(expected_account, 16)

    def test_creation(self):
        assert self.get_account_balance(self.ALICE.address) == 10**12
        assert self.sim.get_storage_data(self.contract, coerce_to_bytes(2**160-1)) == 1
        assert self.sim.get_storage_data(self.contract, coerce_to_bytes(2**160)) == int(self.ALICE.address, 16)

    def test_alice_balance(self):
        ans = self.sim.tx(self.ALICE, self.contract, 0, ["balance", self.ALICE.address])
        assert ans == [10**12]

    def test_alice_pay_to_bob(self):
        ans = self.sim.tx(self.ALICE, self.contract, 0, ["pay", self.BOB.address, 1000])
        assert ans == [1]
        assert self.get_account_balance(self.ALICE.address) == 999999998950
        assert self.get_account_balance(self.BOB.address) == 1000

        # new account gets registered
        self.assert_account_list([self.ALICE.address, self.BOB.address])

        # payment tax added to commons account and tax credits
        assert self.get_commons_balance() == 50
        assert self.get_account_tax_credits(self.ALICE.address) == 50

        # make another payment
        ans = self.sim.tx(self.ALICE, self.contract, 0, ["pay", self.BOB.address, 1000])
        assert ans == [1]
        assert self.get_account_balance(self.ALICE.address) == 999999997900
        assert self.get_account_balance(self.BOB.address) == 2000

        # new account gets registered only once
        self.assert_account_list([self.ALICE.address, self.BOB.address])

    def test_bob_to_charlie_invalid(self):
        ans = self.sim.tx(self.BOB, self.contract, 0, ["pay", self.CHARLIE.address, 1000])
        assert ans[0] == 0
        assert coerce_to_bytes(ans[1]) == "insufficient balance"
        assert self.get_account_balance(self.ALICE.address) == 10**12
        assert self.get_account_balance(self.BOB.address) == 0
        assert self.get_account_balance(self.CHARLIE.address) == 0

    def test_alice_to_bob_to_charlie_valid(self):
        ans = self.sim.tx(self.ALICE, self.contract, 0, ["pay", self.BOB.address, 1000])
        assert ans == [1]

        ans = self.sim.tx(self.BOB, self.contract, 0, ["pay", self.CHARLIE.address, 250])
        assert ans == [1]

        assert self.get_account_balance(self.ALICE.address) == 999999998950
        assert self.get_account_balance(self.BOB.address) == 738
        assert self.get_account_balance(self.CHARLIE.address) == 250

        assert self.get_commons_balance() == 62

        self.assert_account_list([self.ALICE.address, self.BOB.address, self.CHARLIE.address])
