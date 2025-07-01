"""
Unit tests for start handler
Tests for handling repeated /start from declined and pending users
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from telebot.types import Message, User, Chat

# Mock the bot instance and sheets module before importing handlers
with patch('bot.handlers.start.bot', create=True), \
     patch('bot.sheets', create=True):
    from bot.handlers.start import handle_start


class TestStartHandler(unittest.TestCase):
    """Test cases for start handler functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_bot = Mock()
        self.mock_sheets = Mock()
        
        # Create a mock message
        self.mock_user = Mock(spec=User)
        self.mock_user.id = 12345
        self.mock_user.username = "testuser"
        
        self.mock_chat = Mock(spec=Chat)
        self.mock_chat.id = 12345
        
        self.mock_message = Mock(spec=Message)
        self.mock_message.from_user = self.mock_user
        self.mock_message.chat = self.mock_chat
    
    @patch('bot.handlers.start.bot')
    @patch('bot.handlers.start.sheets')
    @patch('bot.handlers.start.ADMIN_IDS', [])
    @patch('bot.handlers.start.notify_admins_new_worker')
    def test_declined_user_repeated_start_no_admin_notification(
        self, 
        mock_notify_admins, 
        mock_sheets, 
        mock_bot
    ):
        """
        Test that declined user gets declined message on repeated /start
        and no admin notification is sent
        """
        # Setup: user with declined status
        mock_sheets.get_worker.return_value = {
            "tg_id": 12345,
            "username": "testuser",
            "role": "declined",
            "clients_count": 0,
            "balance": 0.0
        }
        
        # Execute
        handle_start(self.mock_message)
        
        # Verify: declined message sent
        mock_bot.reply_to.assert_called_once_with(
            self.mock_message,
            "🛑 Your application was declined. Contact admin to reapply."
        )
        
        # Verify: no admin notification sent
        mock_notify_admins.assert_not_called()
        
        # Verify: no new worker added
        mock_sheets.add_worker.assert_not_called()
    
    @patch('bot.handlers.start.bot')
    @patch('bot.handlers.start.sheets')
    @patch('bot.handlers.start.ADMIN_IDS', [])
    @patch('bot.handlers.start.notify_admins_new_worker')
    def test_pending_user_repeated_start_no_admin_notification(
        self, 
        mock_notify_admins, 
        mock_sheets, 
        mock_bot
    ):
        """
        Test that pending user gets pending message on repeated /start
        and no admin notification is sent
        """
        # Setup: user with pending status
        mock_sheets.get_worker.return_value = {
            "tg_id": 12345,
            "username": "testuser",
            "role": "pending",
            "clients_count": 0,
            "balance": 0.0
        }
        
        # Execute
        handle_start(self.mock_message)
        
        # Verify: pending message sent
        mock_bot.reply_to.assert_called_once_with(
            self.mock_message,
            "⏳ Your application is under review."
        )
        
        # Verify: no admin notification sent
        mock_notify_admins.assert_not_called()
        
        # Verify: no new worker added
        mock_sheets.add_worker.assert_not_called()
    
    @patch('bot.handlers.start.bot')
    @patch('bot.handlers.start.sheets')
    @patch('bot.handlers.start.ADMIN_IDS', [])
    @patch('bot.handlers.start.notify_admins_new_worker')
    @patch('bot.handlers.start.show_cabinet')
    def test_worker_user_start_shows_cabinet(
        self, 
        mock_show_cabinet,
        mock_notify_admins, 
        mock_sheets, 
        mock_bot
    ):
        """
        Test that approved worker gets cabinet on /start
        """
        # Setup: user with worker status
        mock_sheets.get_worker.return_value = {
            "tg_id": 12345,
            "username": "testuser",
            "role": "worker",
            "clients_count": 5,
            "balance": 100.0
        }
        
        # Execute
        handle_start(self.mock_message)
        
        # Verify: cabinet shown
        mock_show_cabinet.assert_called_once_with(self.mock_message)
        
        # Verify: no admin notification sent
        mock_notify_admins.assert_not_called()
        
        # Verify: no new worker added
        mock_sheets.add_worker.assert_not_called()
    
    @patch('bot.handlers.start.bot')
    @patch('bot.handlers.start.sheets')
    @patch('bot.handlers.start.ADMIN_IDS', [])
    @patch('bot.handlers.start.notify_admins_new_worker')
    def test_new_user_start_creates_pending_and_notifies_admins(
        self, 
        mock_notify_admins, 
        mock_sheets, 
        mock_bot
    ):
        """
        Test that new user gets pending status and admins are notified
        """
        # Setup: no existing worker record
        mock_sheets.get_worker.return_value = None
        
        # Execute
        handle_start(self.mock_message)
        
        # Verify: new worker added with pending status
        mock_sheets.add_worker.assert_called_once_with(12345, "testuser")
        
        # Verify: admin notification sent
        mock_notify_admins.assert_called_once_with(12345, "testuser")
        
        # Verify: pending message sent to user
        mock_bot.reply_to.assert_called_once_with(
            self.mock_message,
            "📝 Заявка на регистрацию отправлена. "
            "Ожидайте одобрения от администратора."
        )
    
    @patch('bot.handlers.start.bot')
    @patch('bot.handlers.start.sheets')
    @patch('bot.handlers.start.ADMIN_IDS', [12345])
    def test_admin_user_start_shows_admin_message(
        self, 
        mock_sheets, 
        mock_bot
    ):
        """
        Test that admin user gets admin message on /start
        """
        # Execute
        handle_start(self.mock_message)
        
        # Verify: admin message sent
        mock_bot.reply_to.assert_called_once_with(
            self.mock_message,
            "🔧 Вы админ, используйте /admin для панели управления"
        )
        
        # Verify: no worker lookup performed
        mock_sheets.get_worker.assert_not_called()


if __name__ == '__main__':
    unittest.main() 