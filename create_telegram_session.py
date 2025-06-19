from telethon.sync import TelegramClient

api_id = 25817557
api_hash = '7d5b0d255fff646e6dea9e2008d1c1c3'

with TelegramClient('neurofeed_telegram', api_id, api_hash) as client:
    print("Logged in successfully.")
