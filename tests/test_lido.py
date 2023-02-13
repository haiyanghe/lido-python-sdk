import copy
from unittest.mock import PropertyMock

from web3 import Web3

from lido_sdk import Lido
from lido_sdk.methods import (
    get_operators_indexes,
    get_operators_data,
    get_operators_keys,
    validate_keys,
    find_duplicated_keys,
)
from tests.fixtures import OPERATORS_DATA, OPERATORS_KEYS
from tests.utils import get_mainnet_provider, MockTestCase


class LidoE2ETest(MockTestCase):
    def test_main_flow_methods(self):
        w3 = get_mainnet_provider()
        operators_count = get_operators_indexes(w3)[:1]

        operators_data = get_operators_data(w3, operators_count)
        operators_data[0]["totalSigningKeys"] = 30
        keys = get_operators_keys(w3, operators_data)

        invalid_keys = validate_keys(w3, keys)
        duplicates = find_duplicated_keys(keys)

        self.assertListEqual(invalid_keys, [])
        self.assertListEqual(duplicates, [])


class OperatorTest(MockTestCase):
    def setUp(self) -> None:
        self.mocker.patch(
            "web3.eth.Eth.chain_id", return_value=1, new_callable=PropertyMock
        )
        self.w3 = Web3()

        self.lido = Lido(self.w3)

    def test_get_operators_indexes(self):
        self.mocker.patch(
            "lido_sdk.contract.load_contract.NodeOpsContract.getNodeOperatorsCount",
            return_value={"": 5},
        )

        operator_indexes = self.lido.get_operators_indexes()
        self.assertListEqual([x for x in range(5)], operator_indexes)

    def test_get_operators_data(self):
        """We are checking that indexes are assigned correctly"""
        self.mocker.patch(
            "lido_sdk.contract.load_contract.NodeOpsContract.getNodeOperator_multicall",
            return_value=OPERATORS_DATA,
        )

        self.lido.operators_indexes = [0, 1]
        operators_data = self.lido.get_operators_data([0, 1])
        self.assertEqual(2, len(operators_data))
        self.assertEqual(0, operators_data[0]["index"])
        self.assertEqual(1, operators_data[1]["index"])

        """Input is an empty array"""
        self.lido.operators_indexes = [0, 1]
        operators_data = self.lido.get_operators_data([])
        self.assertEqual(0, len(operators_data))

        """Input is None"""
        self.lido.operators_indexes = [0, 1]
        operators_data = self.lido.get_operators_data()
        self.assertEqual(2, len(operators_data))
        self.assertEqual(0, operators_data[0]["index"])
        self.assertEqual(1, operators_data[1]["index"])

    def test_get_operators_keys(self):
        self.mocker.patch(
            "lido_sdk.contract.load_contract.NodeOpsContract.getSigningKey_multicall",
            return_value=OPERATORS_KEYS,
        )

        operators = OPERATORS_DATA[:]

        operators[0]["index"] = 0
        operators[1]["index"] = 1

        keys = self.lido.get_operators_keys(OPERATORS_DATA)

        expected_indexes = [
            {"index": 0, "operator_index": 0},
            {"index": 1, "operator_index": 0},
            {"index": 0, "operator_index": 1},
            {"index": 1, "operator_index": 1},
            {"index": 2, "operator_index": 1},
        ]

        for expected_key, key in zip(expected_indexes, keys):
            self.assertEqual(expected_key["index"], key["index"])
            self.assertEqual(expected_key["operator_index"], key["operator_index"])

        """Input is None"""
        self.lido.operators = OPERATORS_DATA
        keys = self.lido.get_operators_keys()
        self.assertEqual(5, len(keys))

        """Input is an empty array"""
        self.lido.operators = OPERATORS_DATA
        keys = self.lido.get_operators_keys([])
        self.assertEqual(0, len(keys))

    def test_validate_keys(self):
        self.mocker.patch(
            "lido_sdk.contract.load_contract.LidoContract.getWithdrawalCredentials",
            return_value={
                "": b"\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xb9\xd7\x93Hx\xb5\xfb\x96\x10\xb3\xfe\x8a^D\x1e\x8f\xad~)?"
            },
        )

        invalid_keys = self.lido.validate_keys(OPERATORS_KEYS)
        self.assertEqual(2, len(invalid_keys))

        """Forcing lido.keys have invalid keys and input is an empty array"""
        self.lido.keys = OPERATORS_KEYS
        invalid_keys = self.lido.validate_keys([])
        self.assertEqual(0, len(invalid_keys))

        """Forcing lido.keys have invalid keys and input is None"""
        self.lido.keys = OPERATORS_KEYS
        invalid_keys = self.lido.validate_keys()
        self.assertEqual(2, len(invalid_keys))

    def test_find_duplicated_keys(self):
        duplicates = self.lido.find_duplicated_keys(
            [*OPERATORS_KEYS, OPERATORS_KEYS[0]]
        )

        self.assertEqual(1, len(duplicates))
        self.assertEqual(duplicates[0][0]["key"], duplicates[0][1]["key"])

        """Forcing lido.keys are empty and input is None"""
        self.lido.keys = []
        duplicates = self.lido.find_duplicated_keys()
        self.assertEqual(0, len(duplicates))

        """Forcing lido.keys empty array and input is an empty array"""
        self.lido.keys = []
        duplicates = self.lido.find_duplicated_keys([])
        self.assertEqual(0, len(duplicates))

        """Forcing lido.keys have duplicates and input is an empty array"""
        self.lido.keys = [*OPERATORS_KEYS, OPERATORS_KEYS[0]]
        duplicates = self.lido.find_duplicated_keys([])
        self.assertEqual(0, len(duplicates))

        """Forcing lido.keys have duplicates and input is None"""
        self.lido.keys = [*OPERATORS_KEYS, OPERATORS_KEYS[0]]
        duplicates = self.lido.find_duplicated_keys()
        self.assertEqual(1, len(duplicates))
        self.assertEqual(duplicates[0][0]["key"], duplicates[0][1]["key"])

    def test_keys_update(self):
        self.mocker.patch(
            "lido_sdk.contract.load_contract.NodeOpsContract.getNodeOperatorsCount",
            return_value={"": 5},
        )
        self.mocker.patch(
            "lido_sdk.contract.load_contract.NodeOpsContract.getNodeOperator_multicall",
            return_value=OPERATORS_DATA,
        )
        self.mocker.patch(
            "lido_sdk.contract.load_contract.NodeOpsContract.getSigningKey_multicall",
            return_value=OPERATORS_KEYS,
        )

        self.lido.get_operators_indexes()
        self.lido.get_operators_data()
        self.lido.get_operators_keys()

        operators = copy.deepcopy(OPERATORS_DATA)
        operators[0]["totalSigningKeys"] += 2
        operators[0]["usedSigningKeys"] += 1
        operators[1]["totalSigningKeys"] -= 1

        self.mocker.patch(
            "lido_sdk.contract.load_contract.NodeOpsContract.getNodeOperator_multicall",
            return_value=operators,
        )

        keys = copy.deepcopy(
            [
                OPERATORS_KEYS[1].copy(),
                OPERATORS_KEYS[1].copy(),
                OPERATORS_KEYS[1].copy(),
            ]
        )
        keys[0]["used"] = True
        keys[1]["index"] += 1
        keys[2]["index"] += 2
        keys_list_call = self.mocker.patch(
            "lido_sdk.contract.load_contract.NodeOpsContract.getSigningKey_multicall",
            return_value=keys,
        )

        self.lido.update_keys()

        self.assertEqual(len(keys_list_call.call_args[0][1]), 3)

        # Two keys were added (operator 0)
        # One key was removed (operator 1)
        self.assertEqual(len(self.lido.keys), 6)

        key = next(
            (
                key
                for key in self.lido.keys
                if key["index"] == 1 and key["operator_index"] == 0
            )
        )
        self.assertTrue(key["used"])

    def test_keys_update_when_unused_keys_removed(self):
        self.mocker.patch(
            "lido_sdk.contract.load_contract.NodeOpsContract.getNodeOperatorsCount",
            return_value={"": 2},
        )
        self.mocker.patch(
            "lido_sdk.contract.load_contract.NodeOpsContract.getNodeOperator_multicall",
            return_value=OPERATORS_DATA,
        )
        self.mocker.patch(
            "lido_sdk.contract.load_contract.NodeOpsContract.getSigningKey_multicall",
            return_value=OPERATORS_KEYS,
        )

        self.lido.get_operators_indexes()
        self.lido.get_operators_data()
        self.lido.get_operators_keys()

        operators = copy.deepcopy(OPERATORS_DATA)
        # All unused keys were removed (operator 0)
        # All unused keys were removed (operator 1)
        operators[0]["totalSigningKeys"] = 1
        operators[0]["usedSigningKeys"] = 1
        operators[1]["totalSigningKeys"] = 2
        operators[1]["usedSigningKeys"] = 2

        self.mocker.patch(
            "lido_sdk.contract.load_contract.NodeOpsContract.getNodeOperator_multicall",
            return_value=operators,
        )

        self.lido.update_keys()

        # All unused keys were removed (operator 0)
        # All unused keys were removed (operator 1)
        self.assertEqual(len(self.lido.keys), 3)

    def test_keys_bulk_verify(self):
        self.mocker.patch(
            "lido_sdk.contract.load_contract.LidoContract.getWithdrawalCredentials",
            return_value={
                "": b"\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xb9\xd7\x93Hx\xb5\xfb\x96\x10\xb3\xfe\x8a^D\x1e\x8f\xad~)?"
            },
        )

        keys_to_check = [
            OPERATORS_KEYS[0],
            *OPERATORS_KEYS[2:3] * 200 * 2,
            OPERATORS_KEYS[1],
        ]

        invalid_keys = self.lido.validate_keys(keys_to_check)  # 2000 keys
        self.assertEqual(2, len(invalid_keys))

        self.assertEqual(invalid_keys[0], OPERATORS_KEYS[0])
        self.assertEqual(invalid_keys[1], OPERATORS_KEYS[1])
