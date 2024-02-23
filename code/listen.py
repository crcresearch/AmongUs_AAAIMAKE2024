import os
import sys
import json
import time
import random
import numpy as np
import math
import threading
from tiny_agent import Agent
from mastodon import Mastodon, StreamListener

sys.path.append(os.getcwd())

API_BASE_URL = 'ADD_YOUR_MASTODON_SERVER_NAME'
CLIENT_CRED_FILE = 'botz_clientcred.secret'
USER_CRED_FILE = 'botz_usercred.secret'
LOG_DIR = "logs"

def create_mastodon_app():
    Mastodon.create_app(
        'botzapp',
        api_base_url=API_BASE_URL,
        to_file=CLIENT_CRED_FILE
    )


def login_mastodon():
    # try 10 times to login
    for _ in range(10):
        try:
            mastodon = Mastodon(client_id=CLIENT_CRED_FILE, api_base_url=API_BASE_URL)
            mastodon.log_in(MASTODON_EMAIL, MASTODON_PASSWORD, to_file=USER_CRED_FILE)
            print("Logged in")
            return mastodon
        except Exception as e:
            print(e)
            time.sleep(10)

def extract_handle(word):
    # find href and take username after
    word = word.strip()
    href_str = """href="ADD_YOUR_MASTODON_SERVER_NAME"""
    if word.startswith(href_str):
        print(f'found href: {word}')
        print(f'handle is {word.split("/")[3]}')
        return word.split("/")[3][:-1]
    return None

class BotLogic(StreamListener):
    def __init__(self, mastodon):
        self.mastodon = mastodon

    # @staticmethod
    def relevance(self, status):
        #identify post level
        my_act_id = self.mastodon.me()["id"]
        if status["in_reply_to_id"] is None:
            print("level 0, responding")
            return True
        else:
            return random.random() < 0.05 #change percentage based on the requirements

    @staticmethod
    def clean_response(response, handles):
        # response is between <POST> and </POST>
        og_response = response
        try:
            for handle in handles:
                response = response.replace(f" {handle}", "")
            if "<POST>" in response and "</POST>" in response:
                response = response.split("<POST>")[1].split("</POST>")[0]
                response = response.strip()
                response = ' '.join(handles) + ' ' + str(response)
                if response[0] == "\"":
                    response = response[1:]
                if response[-1] == "\"":
                    response = response[:-1]
                return response
            else:
                # remove <POST> and </POST> tags if they are still there
                safe_response = og_response.replace("<POST>", "")
                safe_response = safe_response.replace("</POST>", "")
                safe_response = safe_response.strip()
                safe_response = ' '.join(handles) + ' ' + str(safe_response)
                return safe_response

        except Exception as e:
            print(e)
            return og_response

    # @staticmethod
    def time_to_post(self, status):
        my_act_id = self.mastodon.me()["id"]
        # level 0
        if status["in_reply_to_id"] is None:
            response_time = 30 + math.floor(random.random() * 7200)
            print(f"Responding in {response_time} seconds")
        # level 1+
        else:
            response_time = 30 + math.floor(random.random() * 3600)
        return response_time

    def on_update(self, status):
        print(f"Received an update: {status}")
        
        handles =[]
        own_handle = "@" + MASTODON_ACCT


        # search post for handles and append any
        for word in status['content'].split():
            word = word.strip()
            handle_word = extract_handle(word)
            if handle_word is not None and handle_word not in handles:
                if handle_word == own_handle:
                    print("Ignoring own handle")
                    continue
                handles.append(handle_word)

        handles.append('@' + status['account']['acct'])

        print(f"Handles: {handles}")

        if len(handles) > 2:
            print("Ignoring toot with more than 2 handles")
            return

        if status['account']['acct'] == MASTODON_ACCT:
            print("Ignoring own toot")
            return

        with open(CONFIG_FILE) as f:
            config = json.load(f)

        config["AgentCode"]["objective"] = config["AgentCode"]["objective"].replace(
            "<TWEET>", status['content'])
        agent = Agent(config)
        reply = agent.run()
        print(reply)
        if self.relevance(status=status,):
            response = self.clean_response(reply["response"], handles)
            time_to_post = self.time_to_post(status=status)
            print(f"Decided to respond with: {response}. Posting in {time_to_post} seconds.")

            response_thread = threading.Thread(target=self.delayed_response, args=(response, status, time_to_post))
            response_thread.start()
        else:
            print("Decided not to respond")
            
    def delayed_response(self, response, status, delay):
        """Handles the delayed posting of a response."""
        threading.Event().wait(delay)  # Non-blocking wait
        if len(response) > 500:
            # break into sentences
            response = response.split(".")
            total_chars = 0
            response_str = ""
            for sentence in response:
                if total_chars + len(sentence) > 500:
                    break
                response_str += sentence + "."
                total_chars += len(sentence)
            response = response_str
        if len(response) > 5:
            self.mastodon.status_post(response, in_reply_to_id=status['id'])
            print("Posted")

def extract_login_info(config):
    with open(config, 'r') as file:
        config = json.load(file)
    global MASTODON_ACCT
    global MASTODON_EMAIL
    global MASTODON_PASSWORD
    MASTODON_ACCT = config["login"]["account"]
    MASTODON_EMAIL = config["login"]["email"]
    MASTODON_PASSWORD = config["login"]["password"]

stop_event = threading.Event()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        CONFIG_FILE = sys.argv[1]
        extract_login_info(CONFIG_FILE)
        

    create_mastodon_app()
    mastodon = login_mastodon()
    listener = BotLogic(mastodon)
    mastodon.stream_user(listener, run_async=True)
    while not stop_event.is_set():
        stop_event.wait(timeout=1000)
