import re
import os
import time
import openai
import requests
import colorama
import logging
import subprocess
from contexts import TERMINAL_COMMANDS
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.environ.get("OPENAI_API_KEY")
model_name = os.environ.get("MODEL_NAME")

DEBUG = False
logging.basicConfig(level=logging.WARNING)
message_history = TERMINAL_COMMANDS
READ_RE_PATTERN = r"--r \[(.*?)\]"
WEB_RE_PATTERN = r"--w \[(.*?)\]"

def gpt_query(model=model_name, max_retries=15, sleep_time=2):
    global message_history
    retries = 0
    logger = logging.getLogger()

    logger.info("Message History: %s", message_history)
        
    while retries < max_retries:
        try:
            completion = openai.ChatCompletion.create(
                model=model,
                messages=message_history
            )
            reply_content = completion.choices[0].message.content
            if reply_content:
                return reply_content
        except Exception as e:
            logger.warning("Error during gpt_query(): %s", e)
            retries += 1
            time.sleep(sleep_time)

    raise Exception("Maximum retries exceeded. Check your code for errors.")


def extract_paragraphs(url: str):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    paragraphs: str = ''

    for paragraph in soup.find_all('p'):
        paragraphs += paragraph.text + '\n\n'
    return paragraphs

for _ in range(3): print()
print(f"~{colorama.Style.BRIGHT}\033[4mWelcome to TermGPT{colorama.Style.RESET_ALL}~")
for _ in range(3): print()

print("The goal for TermGPT is to make rapid prototyping with GPT models even quicker and more fluid.")
print()

command_outputs = ""

while True:
    GPT_DONE = False
    print(colorama.Fore.CYAN + colorama.Style.BRIGHT + 'It looks like there is no current input. Please provide your objectives. \n"' 
+ colorama.Fore.YELLOW + '--c' + colorama.Fore.CYAN + '" to clear contextual history. \n"' 
+ colorama.Fore.YELLOW + '--o' + colorama.Fore.CYAN + '" to parse previous console command outputs and suggest further commands (can be helpful for big errors)\n"' 
+ colorama.Fore.YELLOW + '--w' + colorama.Fore.CYAN + '" to parse a website into context \n"' 
+ colorama.Fore.YELLOW + '--r [path/to/file.py]' + colorama.Fore.CYAN + '" to open and read some file into context (can do multiple files, and is embedded into some prompt.) Example: "Please change --r [mplexample.py] to be a dark theme"'+ colorama.Style.RESET_ALL)

    init_input = input(colorama.Fore.GREEN + colorama.Style.BRIGHT + "Command: " + colorama.Style.RESET_ALL)

    if init_input.lower() == "clear"  or init_input.lower() == "--c":
        message_history = TERMINAL_COMMANDS
        command_outputs = ""
        print(colorama.Fore.YELLOW + colorama.Style.BRIGHT + "Context reset.\n\n" + colorama.Style.RESET_ALL)
        continue

    elif init_input.lower() == "output" or init_input.lower() == "--o":
        user_input = "NEW STARTING INPUT: I received the following console outputs after running everything. Is there anything I should do to address any errors, warnings, or notifications?: \n" + command_outputs

    else:
        matches = re.findall(READ_RE_PATTERN, init_input)
        match_content = {}
        if matches:
            for n, match in enumerate(matches):
                with open(match, "r") as f:
                    match_content[match] = f.read()

        web_matches = re.findall(WEB_RE_PATTERN, init_input)
        web_match_content = {}
        if web_matches:
            for n, web_match in enumerate(web_matches):
                web_match_content[web_match] = extract_paragraphs(web_match)

        for match in match_content:
            original = f"--r [{match}]"
            replacement = f"\n file: {match}\n{match_content[match]}\n"
            init_input = init_input.replace(original, replacement)

        for web_match in web_match_content:
            original = f"--w [{web_match}]"
            replacement = f"\n website content: {web_match}\n{web_match_content[web_match]}\n"
            init_input = init_input.replace(original, replacement)

        user_input = "NEW STARTING INPUT: " + init_input

    if DEBUG:
        print()
        print()
        print("User Input:")
        print()
        print(colorama.Fore.MAGENTA + colorama.Style.DIM + user_input + colorama.Style.RESET_ALL)
        print()
        print()

    message_history.append({"role": "user", "content": user_input})

    commands = []

    while not GPT_DONE:
        print(colorama.Fore.GREEN + colorama.Style.DIM + "Querying GPT for next command (these are not running yet)..." + colorama.Style.RESET_ALL)
        reply_content = gpt_query(model=model_name)

        message_history.append({"role": "assistant", "content": reply_content})
        message_history.append({"role": "user", "content": "NEXT"})
        print(colorama.Fore.WHITE + colorama.Style.DIM + reply_content + colorama.Style.RESET_ALL)

        if reply_content.lower().startswith("done"):
            GPT_DONE = True
            print(colorama.Fore.YELLOW + colorama.Style.BRIGHT + "Done reached." + colorama.Style.RESET_ALL)
            break
        else:
            commands.append(reply_content)
        time.sleep(1.5)

    print(colorama.Fore.CYAN + colorama.Style.BRIGHT + "Proposed Commands:" + colorama.Style.RESET_ALL)
    for n, command in enumerate(commands):
        print(colorama.Fore.WHITE + colorama.Style.BRIGHT + "-"*5 + "Command "+ str(n)+ "-"*5 + colorama.Style.RESET_ALL)
        print()
        print(colorama.Fore.RED + colorama.Style.BRIGHT + command + colorama.Style.RESET_ALL)
        print()

    if len(commands) > 0:
        print(colorama.Fore.CYAN + colorama.Style.BRIGHT + "Would you like to run these commands? " + colorama.Fore.YELLOW + "Read carefully!" + colorama.Style.RESET_ALL + colorama.Fore.CYAN + colorama.Style.BRIGHT + " Do not run if you don't understand and want the outcomes. (y/n)" + colorama.Style.RESET_ALL)

        run_commands = input("Run the commands? (y/n): ")
        if run_commands.lower() == "y":
            for n, command in enumerate(commands):


                try:
                    print(colorama.Fore.CYAN + colorama.Style.BRIGHT + "Running command " + str(n) + ": " + command + colorama.Style.RESET_ALL)
                    output = subprocess.check_output(command, shell=True, text=True).strip()
                    
                except subprocess.CalledProcessError as e:
                    print(colorama.Fore.YELLOW + colorama.Style.DIM + "Error during command execution: " + str(e) + colorama.Style.RESET_ALL)
                    output = e.output.strip()

                print(output)
                command_outputs += output + "\n\n"
        else:
            print(colorama.Fore.CYAN + colorama.Style.BRIGHT + "Okay, not running commands." + colorama.Style.RESET_ALL)
