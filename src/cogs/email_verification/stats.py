from datetime import datetime, timedelta
import json
import aiofiles
from collections import defaultdict
import logging

logger = logging.getLogger('email_verification')

class VerificationStats:
   def __init__(self):
       self.stats_file = "verification_stats.json"
       self.daily_stats = defaultdict(self._create_default_stats)
       self.load_stats()

   @staticmethod
   def _create_default_stats():
       return {
           'total_attempts': 0,
           'successful_verifications': 0,
           'failed_verifications': 0,
           'expired_verifications': 0,
           'invalid_emails': 0,
           'already_verified_attempts': 0,
           'email_send_errors': 0,
           'invalid_codes': 0,
           'domains': defaultdict(int)
       }

   def load_stats(self):
       try:
           with open(self.stats_file, 'r') as f:
               loaded_stats = json.load(f)
               self.daily_stats = defaultdict(self._create_default_stats)
               for date, stats in loaded_stats.items():
                   self.daily_stats[date] = stats
                   self.daily_stats[date]['domains'] = defaultdict(int, stats['domains'])
       except FileNotFoundError:
           self.save_stats()
       except json.JSONDecodeError as e:
           logger.error(f"Failed to decode stats file: {e}")
           self.daily_stats = defaultdict(self._create_default_stats)
           self.save_stats()
       except Exception as e:
           logger.error(f"Error loading stats: {e}")
           self.daily_stats = defaultdict(self._create_default_stats)
           self.save_stats()

   async def save_stats(self):
       try:
           stats_dict = {date: {
               **stats,
               'domains': dict(stats['domains'])
           } for date, stats in self.daily_stats.items()}
           
           async with aiofiles.open(self.stats_file, 'w') as f:
               await f.write(json.dumps(stats_dict, indent=2))
       except Exception as e:
           logger.error(f"Error saving stats: {e}")

   def get_today_key(self):
       return datetime.now().strftime('%Y-%m-%d')

   async def log_verification_attempt(self, email: str):
       try:
           today = self.get_today_key()
           self.daily_stats[today]['total_attempts'] += 1
           domain = email.split('@')[-1]
           self.daily_stats[today]['domains'][domain] += 1
           await self.save_stats()
       except Exception as e:
           logger.error(f"Error logging verification attempt: {e}")

   async def log_verification_success(self):
       try:
           today = self.get_today_key()
           self.daily_stats[today]['successful_verifications'] += 1
           await self.save_stats()
       except Exception as e:
           logger.error(f"Error logging verification success: {e}")

   async def log_verification_failure(self, reason: str):
       try:
           today = self.get_today_key()
           self.daily_stats[today]['failed_verifications'] += 1
           if reason in ['expired', 'invalid_email', 'already_verified', 'email_error', 'invalid_code']:
               key = f'{reason}_verifications' if reason == 'expired' else reason
               self.daily_stats[today][key] += 1
           await self.save_stats()
       except Exception as e:
           logger.error(f"Error logging verification failure: {e}")

   async def get_stats_report(self, days: int = 7) -> dict:
       try:
           end_date = datetime.now()
           start_date = end_date - timedelta(days=days)
           
           total_stats = {
               'total_attempts': 0,
               'successful_verifications': 0,
               'failed_verifications': 0,
               'expired_verifications': 0,
               'invalid_emails': 0,
               'already_verified_attempts': 0,
               'email_send_errors': 0,
               'invalid_codes': 0,
               'success_rate': 0,
               'domains': defaultdict(int),
               'daily_breakdown': {}
           }
           
           current_date = start_date
           while current_date <= end_date:
               date_key = current_date.strftime('%Y-%m-%d')
               if date_key in self.daily_stats:
                   day_stats = self.daily_stats[date_key]
                   total_stats['daily_breakdown'][date_key] = day_stats
                   
                   # Aggregate stats
                   total_stats['total_attempts'] += day_stats['total_attempts']
                   total_stats['successful_verifications'] += day_stats['successful_verifications']
                   total_stats['failed_verifications'] += day_stats['failed_verifications']
                   total_stats['expired_verifications'] += day_stats['expired_verifications']
                   total_stats['invalid_emails'] += day_stats['invalid_emails']
                   total_stats['already_verified_attempts'] += day_stats['already_verified_attempts']
                   total_stats['email_send_errors'] += day_stats['email_send_errors']
                   total_stats['invalid_codes'] += day_stats['invalid_codes']
                   
                   # Aggregate domains
                   for domain, count in day_stats['domains'].items():
                       total_stats['domains'][domain] += count
               
               current_date += timedelta(days=1)
           
           # Calculate success rate
           if total_stats['total_attempts'] > 0:
               total_stats['success_rate'] = (total_stats['successful_verifications'] / 
                                            total_stats['total_attempts']) * 100
           
           return total_stats
       except Exception as e:
           logger.error(f"Error generating stats report: {e}")
           return {}
