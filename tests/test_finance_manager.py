import unittest
from unittest.mock import patch, MagicMock
from modulo.transaction import FinanceManager
from modulo.models import Transaction, Category

class TestFinanceManager(unittest.TestCase):
    def setUp(self):
        self.manager = FinanceManager()

    @patch('modulo.db_helper.get_all_categories')
    @patch('modulo.db_helper.create_transaction')
    def test_add_transaction_income(self, mock_create, mock_get_cats):
        # Giả lập category "Salary" (ID: 1, Type: 1 - Thu)
        mock_get_cats.return_value = [
            {'id': 1, 'key': 'salary', 'value': 'Lương', 'type': 1}
        ]
        
        self.manager.add_transaction(1000, 1, "Tháng 3")
        
        # Kiểm tra xem create_transaction có được gọi với amount dương không
        args, _ = mock_create.call_args
        self.assertEqual(args[1], 1000)

    @patch('modulo.db_helper.get_all_categories')
    @patch('modulo.db_helper.create_transaction')
    def test_add_transaction_expense(self, mock_create, mock_get_cats):
        # Giả lập category "Food" (ID: 2, Type: 0 - Chi)
        mock_get_cats.return_value = [
            {'id': 2, 'key': 'food', 'value': 'Ăn uống', 'type': 0}
        ]
        
        self.manager.add_transaction(500, 2, "Bữa trưa")
        
        # Kiểm tra xem create_transaction có được gọi với amount âm không
        args, _ = mock_create.call_args
        self.assertEqual(args[1], -500)

    @patch('modulo.db_helper.get_all_categories')
    def test_add_transaction_invalid_category(self, mock_get_cats):
        mock_get_cats.return_value = []
        
        with self.assertRaises(ValueError):
            self.manager.add_transaction(100, 999)

if __name__ == '__main__':
    unittest.main()
