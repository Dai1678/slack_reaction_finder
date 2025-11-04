#!/usr/bin/env python3
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import argparse
from datetime import datetime, timedelta
from reaction_finder import (
    parse_arguments,
    validate_token,
    build_date_query,
    fetch_message_details,
    search_and_analyze,
    DEFAULT_MAX_SEARCH_RESULTS,
    ENV_TOKEN_NAME,
    DATE_FORMAT
)


class TestParseArguments(unittest.TestCase):
    """Test case 1: parse_arguments correctly parses all arguments and handles validation for --max"""
    
    def test_parse_basic_arguments(self):
        """Test parsing of basic required and optional arguments"""
        test_args = ['test_script', 'pray', '-n', '5', '-t', 'xoxb-test-token']
        with patch.object(sys, 'argv', test_args):
            args = parse_arguments()
            self.assertEqual(args.emoji, 'pray')
            self.assertEqual(args.top, 5)
            self.assertEqual(args.token, 'xoxb-test-token')
            self.assertEqual(args.max, DEFAULT_MAX_SEARCH_RESULTS)
    
    def test_parse_date_arguments(self):
        """Test parsing of date-related arguments"""
        test_args = ['test_script', 'thanks', '--after', '2024-01-01', '--before', '2024-12-31']
        with patch.object(sys, 'argv', test_args):
            args = parse_arguments()
            self.assertEqual(args.after, '2024-01-01')
            self.assertEqual(args.before, '2024-12-31')
    
    def test_parse_days_argument(self):
        """Test parsing of --days argument"""
        test_args = ['test_script', 'tada', '--days', '30']
        with patch.object(sys, 'argv', test_args):
            args = parse_arguments()
            self.assertEqual(args.days, 30)
    
    def test_max_default_value(self):
        """Test that --max defaults to DEFAULT_MAX_SEARCH_RESULTS"""
        test_args = ['test_script', 'pray']
        with patch.object(sys, 'argv', test_args):
            args = parse_arguments()
            self.assertEqual(args.max, DEFAULT_MAX_SEARCH_RESULTS)
    
    def test_max_custom_value(self):
        """Test parsing custom --max value"""
        test_args = ['test_script', 'pray', '--max', '200']
        with patch.object(sys, 'argv', test_args):
            args = parse_arguments()
            self.assertEqual(args.max, 200)
    
    def test_max_validation_less_than_one(self):
        """Test that --max < 1 raises an error"""
        test_args = ['test_script', 'pray', '--max', '0']
        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit):
                parse_arguments()
    
    def test_max_validation_negative(self):
        """Test that negative --max raises an error"""
        test_args = ['test_script', 'pray', '--max', '-5']
        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit):
                parse_arguments()
    
    @patch('builtins.print')
    def test_max_warning_over_1000(self, mock_print):
        """Test that --max > 1000 shows a warning"""
        test_args = ['test_script', 'pray', '--max', '1500']
        with patch.object(sys, 'argv', test_args):
            args = parse_arguments()
            self.assertEqual(args.max, 1500)
            # Check that warning was printed
            mock_print.assert_called_once()
            self.assertIn('1000', str(mock_print.call_args))
    
    def test_token_from_environment(self):
        """Test that token defaults to environment variable"""
        test_args = ['test_script', 'pray']
        with patch.object(sys, 'argv', test_args):
            with patch.dict('os.environ', {ENV_TOKEN_NAME: 'env-token'}):
                args = parse_arguments()
                self.assertEqual(args.token, 'env-token')


class TestValidateToken(unittest.TestCase):
    """Test case 2: validate_token exits when no token is provided"""
    
    @patch('builtins.print')
    def test_validate_token_none(self, mock_print):
        """Test that None token causes exit"""
        with self.assertRaises(SystemExit) as cm:
            validate_token(None)
        self.assertEqual(cm.exception.code, 1)
        # Verify error message was printed
        self.assertTrue(mock_print.called)
        call_args_str = ''.join([str(call) for call in mock_print.call_args_list])
        self.assertIn('Slack Token', call_args_str)
    
    @patch('builtins.print')
    def test_validate_token_empty_string(self, mock_print):
        """Test that empty string token causes exit"""
        with self.assertRaises(SystemExit) as cm:
            validate_token('')
        self.assertEqual(cm.exception.code, 1)
        self.assertTrue(mock_print.called)
    
    def test_validate_token_valid(self):
        """Test that valid token does not cause exit"""
        # Should not raise any exception
        try:
            validate_token('xoxb-valid-token')
        except SystemExit:
            self.fail("validate_token raised SystemExit with valid token")


class TestBuildDateQuery(unittest.TestCase):
    """Test case 3: build_date_query generates correct date query strings for various date argument combinations and validates date ranges"""
    
    def test_no_date_arguments(self):
        """Test empty query when no date arguments provided"""
        args = argparse.Namespace(after=None, before=None, days=None)
        query = build_date_query(args)
        self.assertEqual(query, '')
    
    def test_after_only(self):
        """Test query with only --after"""
        args = argparse.Namespace(after='2024-01-01', before=None, days=None)
        query = build_date_query(args)
        self.assertEqual(query, 'after:2024-01-01')
    
    def test_before_only(self):
        """Test query with only --before"""
        args = argparse.Namespace(after=None, before='2024-12-31', days=None)
        query = build_date_query(args)
        self.assertEqual(query, 'before:2024-12-31')
    
    def test_after_and_before(self):
        """Test query with both --after and --before"""
        args = argparse.Namespace(after='2024-01-01', before='2024-12-31', days=None)
        query = build_date_query(args)
        self.assertEqual(query, 'after:2024-01-01 before:2024-12-31')
    
    @patch('reaction_finder.datetime')
    def test_days_only(self, mock_datetime):
        """Test query with only --days (calculates from today)"""
        mock_now = datetime(2024, 2, 15, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime = datetime.strptime
        
        args = argparse.Namespace(after=None, before=None, days=30)
        query = build_date_query(args)
        
        expected_date = (mock_now - timedelta(days=30)).strftime(DATE_FORMAT)
        self.assertEqual(query, f'after:{expected_date}')
    
    def test_days_with_before(self):
        """Test query with --days and --before (calculates backwards from before date)"""
        args = argparse.Namespace(after=None, before='2024-12-31', days=90)
        query = build_date_query(args)
        
        end_date = datetime.strptime('2024-12-31', DATE_FORMAT)
        start_date = (end_date - timedelta(days=90)).strftime(DATE_FORMAT)
        self.assertEqual(query, f'after:{start_date} before:2024-12-31')
    
    def test_invalid_after_date_format(self):
        """Test that invalid --after date format raises ValueError"""
        args = argparse.Namespace(after='2024/01/01', before=None, days=None)
        with self.assertRaises(ValueError) as cm:
            build_date_query(args)
        self.assertIn('after', str(cm.exception).lower())
    
    def test_invalid_before_date_format(self):
        """Test that invalid --before date format raises ValueError"""
        args = argparse.Namespace(after=None, before='12-31-2024', days=None)
        with self.assertRaises(ValueError) as cm:
            build_date_query(args)
        self.assertIn('before', str(cm.exception).lower())
    
    def test_invalid_before_date_format_with_days(self):
        """Test that invalid --before date format with --days raises ValueError"""
        args = argparse.Namespace(after=None, before='invalid-date', days=30)
        with self.assertRaises(ValueError) as cm:
            build_date_query(args)
        self.assertIn('before', str(cm.exception).lower())
    
    def test_after_greater_than_before(self):
        """Test that --after > --before raises ValueError"""
        args = argparse.Namespace(after='2024-12-31', before='2024-01-01', days=None)
        with self.assertRaises(ValueError) as cm:
            build_date_query(args)
        self.assertIn('不正', str(cm.exception))
        self.assertIn('2024-12-31', str(cm.exception))
        self.assertIn('2024-01-01', str(cm.exception))
    
    def test_valid_date_range(self):
        """Test that valid date range (after < before) works correctly"""
        args = argparse.Namespace(after='2024-01-01', before='2024-12-31', days=None)
        query = build_date_query(args)
        self.assertEqual(query, 'after:2024-01-01 before:2024-12-31')

    def test_same_date_for_after_and_before(self):
        """Test that same date for --after and --before uses 'on:' operator"""
        args = argparse.Namespace(after='2024-06-15', before='2024-06-15', days=None)
        query = build_date_query(args)
        self.assertEqual(query, 'on:2024-06-15')


class TestFetchMessageDetails(unittest.TestCase):
    """Test case 4: fetch_message_details extracts message information and the target emoji reaction count, handling missing reactions or emoji"""
    
    def test_fetch_message_with_target_emoji(self):
        """Test successful extraction of message with target emoji reaction"""
        mock_client = Mock()
        mock_client.conversations_history.return_value = {
            'messages': [{
                'text': 'Great work!',
                'user': 'U12345',
                'reactions': [
                    {'name': 'pray', 'count': 5},
                    {'name': 'thanks', 'count': 3}
                ]
            }]
        }
        mock_client.users_info.return_value = {
            'user': {'real_name': 'John Doe'}
        }
        
        match = {
            'channel': {'id': 'C123', 'name': 'general'},
            'ts': '1609459200.000000',
            'permalink': 'https://slack.com/archives/C123/p1609459200000000'
        }
        
        result = fetch_message_details(mock_client, match, 'pray')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['text'], 'Great work!')
        self.assertEqual(result['user'], 'John Doe')
        self.assertEqual(result['count'], 5)
        self.assertEqual(result['channel_name'], 'general')
        self.assertEqual(result['timestamp'], '1609459200.000000')
        self.assertEqual(result['permalink'], 'https://slack.com/archives/C123/p1609459200000000')
        self.assertIsInstance(result['datetime'], datetime)
    
    def test_fetch_message_with_multiple_reactions(self):
        """Test extraction when message has multiple reactions"""
        mock_client = Mock()
        mock_client.conversations_history.return_value = {
            'messages': [{
                'text': 'Test message',
                'user': 'U12345',
                'reactions': [
                    {'name': 'thumbsup', 'count': 10},
                    {'name': 'tada', 'count': 7},
                    {'name': 'pray', 'count': 2}
                ]
            }]
        }
        mock_client.users_info.return_value = {
            'user': {'real_name': 'Jane Doe'}
        }
        
        match = {
            'channel': {'id': 'C123', 'name': 'random'},
            'ts': '1609459200.000000',
            'permalink': 'https://slack.com/link'
        }
        
        result = fetch_message_details(mock_client, match, 'tada')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['count'], 7)
    
    def test_fetch_message_missing_reactions(self):
        """Test that None is returned when message has no reactions"""
        mock_client = Mock()
        mock_client.conversations_history.return_value = {
            'messages': [{
                'text': 'No reactions here',
                'user': 'U12345'
            }]
        }
        
        match = {
            'channel': {'id': 'C123', 'name': 'general'},
            'ts': '1609459200.000000',
            'permalink': 'https://slack.com/link'
        }
        
        result = fetch_message_details(mock_client, match, 'pray')
        
        self.assertIsNone(result)
    
    def test_fetch_message_target_emoji_not_found(self):
        """Test that None is returned when target emoji is not in reactions"""
        mock_client = Mock()
        mock_client.conversations_history.return_value = {
            'messages': [{
                'text': 'Message with other reactions',
                'user': 'U12345',
                'reactions': [
                    {'name': 'thumbsup', 'count': 5},
                    {'name': 'thanks', 'count': 3}
                ]
            }]
        }
        
        match = {
            'channel': {'id': 'C123', 'name': 'general'},
            'ts': '1609459200.000000',
            'permalink': 'https://slack.com/link'
        }
        
        result = fetch_message_details(mock_client, match, 'pray')
        
        self.assertIsNone(result)
    
    def test_fetch_message_empty_messages(self):
        """Test that None is returned when no messages found"""
        mock_client = Mock()
        mock_client.conversations_history.return_value = {
            'messages': []
        }
        
        match = {
            'channel': {'id': 'C123', 'name': 'general'},
            'ts': '1609459200.000000',
            'permalink': 'https://slack.com/link'
        }
        
        result = fetch_message_details(mock_client, match, 'pray')
        
        self.assertIsNone(result)
    
    def test_fetch_message_no_text(self):
        """Test that default text is used when message has no text"""
        mock_client = Mock()
        mock_client.conversations_history.return_value = {
            'messages': [{
                'user': 'U12345',
                'reactions': [
                    {'name': 'pray', 'count': 5}
                ]
            }]
        }
        mock_client.users_info.return_value = {
            'user': {'real_name': 'John Doe'}
        }
        
        match = {
            'channel': {'id': 'C123', 'name': 'general'},
            'ts': '1609459200.000000',
            'permalink': 'https://slack.com/link'
        }
        
        result = fetch_message_details(mock_client, match, 'pray')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['text'], '(テキストなし)')
    
    @patch('builtins.print')
    def test_fetch_message_api_error_not_channel_not_found(self, mock_print):
        """Test that API errors other than channel_not_found are printed"""
        from slack_sdk.errors import SlackApiError
        
        mock_client = Mock()
        error_response = {'error': 'rate_limited'}
        mock_client.conversations_history.side_effect = SlackApiError(
            message='Rate limited',
            response=error_response
        )
        
        match = {
            'channel': {'id': 'C123', 'name': 'general'},
            'ts': '1609459200.000000',
            'permalink': 'https://slack.com/link'
        }
        
        result = fetch_message_details(mock_client, match, 'pray')
        
        self.assertIsNone(result)
        self.assertTrue(mock_print.called)
    
    def test_fetch_message_channel_not_found_silent(self):
        """Test that channel_not_found error is silently ignored"""
        from slack_sdk.errors import SlackApiError
        
        mock_client = Mock()
        error_response = {'error': 'channel_not_found'}
        mock_client.conversations_history.side_effect = SlackApiError(
            message='Channel not found',
            response=error_response
        )
        
        match = {
            'channel': {'id': 'C123', 'name': 'general'},
            'ts': '1609459200.000000',
            'permalink': 'https://slack.com/link'
        }
        
        result = fetch_message_details(mock_client, match, 'pray')
        
        self.assertIsNone(result)


class TestSearchAndAnalyze(unittest.TestCase):
    """Test case 5: search_and_analyze handles pagination, limits results to max_results, and sorts messages by reaction count"""
    
    @patch('builtins.print')
    @patch('reaction_finder.fetch_message_details')
    def test_search_single_page(self, mock_fetch, mock_print):
        """Test search with results fitting in a single page"""
        mock_client = Mock()
        mock_client.search_messages.return_value = {
            'messages': {
                'total': 50,
                'matches': [
                    {'channel': {'id': 'C1', 'name': 'general'}, 'ts': '1.0', 'permalink': 'link1'},
                    {'channel': {'id': 'C2', 'name': 'random'}, 'ts': '2.0', 'permalink': 'link2'}
                ]
            }
        }
        
        mock_fetch.side_effect = [
            {'text': 'msg1', 'count': 5, 'user': 'u1', 'channel_name': 'general', 
             'timestamp': '1.0', 'datetime': datetime.now(), 'permalink': 'link1'},
            {'text': 'msg2', 'count': 10, 'user': 'u2', 'channel_name': 'random',
             'timestamp': '2.0', 'datetime': datetime.now(), 'permalink': 'link2'}
        ]
        
        results = search_and_analyze(mock_client, 'has::pray:', 'pray', 100)
        
        self.assertEqual(len(results), 2)
        # Verify sorting by count (descending)
        self.assertEqual(results[0]['count'], 10)
        self.assertEqual(results[1]['count'], 5)
        mock_client.search_messages.assert_called_once()
    
    @patch('builtins.print')
    @patch('reaction_finder.fetch_message_details')
    def test_search_pagination(self, mock_fetch, mock_print):
        """Test that pagination occurs when max_results exceeds API limit"""
        mock_client = Mock()
        
        # First page: 100 results
        first_page_matches = [
            {'channel': {'id': f'C{i}', 'name': 'general'}, 'ts': f'{i}.0', 'permalink': f'link{i}'}
            for i in range(100)
        ]
        # Second page: 50 results
        second_page_matches = [
            {'channel': {'id': f'C{i}', 'name': 'general'}, 'ts': f'{i}.0', 'permalink': f'link{i}'}
            for i in range(100, 150)
        ]
        
        mock_client.search_messages.side_effect = [
            {'messages': {'total': 150, 'matches': first_page_matches}},
            {'messages': {'total': 150, 'matches': second_page_matches}}
        ]
        
        # Mock fetch to return all results
        mock_fetch.side_effect = [
            {'text': f'msg{i}', 'count': i, 'user': 'u', 'channel_name': 'general',
             'timestamp': f'{i}.0', 'datetime': datetime.now(), 'permalink': f'link{i}'}
            for i in range(150)
        ]
        
        results = search_and_analyze(mock_client, 'has::pray:', 'pray', 150)
        
        # Should have made 2 API calls
        self.assertEqual(mock_client.search_messages.call_count, 2)
        # Should have 150 results
        self.assertEqual(len(results), 150)
    
    @patch('builtins.print')
    @patch('reaction_finder.fetch_message_details')
    def test_limits_to_max_results(self, mock_fetch, mock_print):
        """Test that results are limited to max_results even when more are available"""
        mock_client = Mock()
        
        # Return 100 matches but max_results is 50
        matches = [
            {'channel': {'id': f'C{i}', 'name': 'general'}, 'ts': f'{i}.0', 'permalink': f'link{i}'}
            for i in range(100)
        ]
        
        mock_client.search_messages.return_value = {
            'messages': {'total': 500, 'matches': matches}
        }
        
        mock_fetch.side_effect = [
            {'text': f'msg{i}', 'count': i, 'user': 'u', 'channel_name': 'general',
             'timestamp': f'{i}.0', 'datetime': datetime.now(), 'permalink': f'link{i}'}
            for i in range(100)
        ]
        
        results = search_and_analyze(mock_client, 'has::pray:', 'pray', 50)
        
        # Should stop at 50 results
        self.assertEqual(len(results), 50)
        # Verify that only 50 were requested in the API call
        call_args = mock_client.search_messages.call_args
        self.assertEqual(call_args[1]['count'], 50)
    
    @patch('builtins.print')
    @patch('reaction_finder.fetch_message_details')
    def test_sorts_by_reaction_count(self, mock_fetch, mock_print):
        """Test that results are sorted by reaction count in descending order"""
        mock_client = Mock()
        mock_client.search_messages.return_value = {
            'messages': {
                'total': 5,
                'matches': [
                    {'channel': {'id': 'C1'}, 'ts': '1.0', 'permalink': 'l1'},
                    {'channel': {'id': 'C2'}, 'ts': '2.0', 'permalink': 'l2'},
                    {'channel': {'id': 'C3'}, 'ts': '3.0', 'permalink': 'l3'},
                    {'channel': {'id': 'C4'}, 'ts': '4.0', 'permalink': 'l4'},
                    {'channel': {'id': 'C5'}, 'ts': '5.0', 'permalink': 'l5'}
                ]
            }
        }
        
        # Return messages with varying counts (not in order)
        mock_fetch.side_effect = [
            {'text': 'msg1', 'count': 3, 'user': 'u1', 'channel_name': 'c1',
             'timestamp': '1.0', 'datetime': datetime.now(), 'permalink': 'l1'},
            {'text': 'msg2', 'count': 10, 'user': 'u2', 'channel_name': 'c2',
             'timestamp': '2.0', 'datetime': datetime.now(), 'permalink': 'l2'},
            {'text': 'msg3', 'count': 1, 'user': 'u3', 'channel_name': 'c3',
             'timestamp': '3.0', 'datetime': datetime.now(), 'permalink': 'l3'},
            {'text': 'msg4', 'count': 7, 'user': 'u4', 'channel_name': 'c4',
             'timestamp': '4.0', 'datetime': datetime.now(), 'permalink': 'l4'},
            {'text': 'msg5', 'count': 5, 'user': 'u5', 'channel_name': 'c5',
             'timestamp': '5.0', 'datetime': datetime.now(), 'permalink': 'l5'}
        ]
        
        results = search_and_analyze(mock_client, 'has::pray:', 'pray', 100)
        
        # Verify sorted in descending order
        self.assertEqual(len(results), 5)
        self.assertEqual(results[0]['count'], 10)
        self.assertEqual(results[1]['count'], 7)
        self.assertEqual(results[2]['count'], 5)
        self.assertEqual(results[3]['count'], 3)
        self.assertEqual(results[4]['count'], 1)
    
    @patch('builtins.print')
    @patch('reaction_finder.fetch_message_details')
    def test_filters_none_results(self, mock_fetch, mock_print):
        """Test that messages without target emoji are filtered out"""
        mock_client = Mock()
        mock_client.search_messages.return_value = {
            'messages': {
                'total': 3,
                'matches': [
                    {'channel': {'id': 'C1'}, 'ts': '1.0', 'permalink': 'l1'},
                    {'channel': {'id': 'C2'}, 'ts': '2.0', 'permalink': 'l2'},
                    {'channel': {'id': 'C3'}, 'ts': '3.0', 'permalink': 'l3'}
                ]
            }
        }
        
        # Some messages don't have the target emoji
        mock_fetch.side_effect = [
            {'text': 'msg1', 'count': 5, 'user': 'u1', 'channel_name': 'c1',
             'timestamp': '1.0', 'datetime': datetime.now(), 'permalink': 'l1'},
            None,  # No target emoji
            {'text': 'msg3', 'count': 3, 'user': 'u3', 'channel_name': 'c3',
             'timestamp': '3.0', 'datetime': datetime.now(), 'permalink': 'l3'}
        ]
        
        results = search_and_analyze(mock_client, 'has::pray:', 'pray', 100)
        
        # Should only have 2 results (one filtered out)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['count'], 5)
        self.assertEqual(results[1]['count'], 3)
    
    @patch('builtins.print')
    @patch('reaction_finder.fetch_message_details')
    def test_empty_search_results(self, mock_fetch, mock_print):
        """Test handling of empty search results"""
        mock_client = Mock()
        mock_client.search_messages.return_value = {
            'messages': {
                'total': 0,
                'matches': []
            }
        }
        
        results = search_and_analyze(mock_client, 'has::pray:', 'pray', 100)
        
        self.assertEqual(len(results), 0)
        mock_fetch.assert_not_called()
    
    @patch('builtins.print')
    @patch('reaction_finder.fetch_message_details')
    def test_pagination_stops_at_exact_max(self, mock_fetch, mock_print):
        """Test that pagination stops exactly at max_results"""
        mock_client = Mock()
        
        # First page: 100 results
        first_page = [
            {'channel': {'id': f'C{i}'}, 'ts': f'{i}.0', 'permalink': f'l{i}'}
            for i in range(100)
        ]
        # Second page: would have more, but we only need 20 more
        second_page = [
            {'channel': {'id': f'C{i}'}, 'ts': f'{i}.0', 'permalink': f'l{i}'}
            for i in range(100, 150)
        ]
        
        mock_client.search_messages.side_effect = [
            {'messages': {'total': 500, 'matches': first_page}},
            {'messages': {'total': 500, 'matches': second_page}}
        ]
        
        mock_fetch.side_effect = [
            {'text': f'msg{i}', 'count': i, 'user': 'u', 'channel_name': 'c',
             'timestamp': f'{i}.0', 'datetime': datetime.now(), 'permalink': f'l{i}'}
            for i in range(150)
        ]
        
        results = search_and_analyze(mock_client, 'has::pray:', 'pray', 120)
        
        # Should have exactly 120 results
        self.assertEqual(len(results), 120)
        # Second call should request only 20 items
        second_call_args = mock_client.search_messages.call_args_list[1]
        self.assertEqual(second_call_args[1]['count'], 20)


if __name__ == '__main__':
    unittest.main()
