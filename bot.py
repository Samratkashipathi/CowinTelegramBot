import logging
import re

import requests
from telegram.ext import Updater, CommandHandler, RegexHandler

# Enable logging
from config import TOKEN

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def get_data(url: str):
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Could not complete the request")
    return response.json()


def help(update, context):
    """Send a message when the command /help is issued."""
    commands = [
        "/states - Return list of state id and state name"
    ]
    update.message.reply_text("\n".join(commands))


def get_states(update, context):
    """Send a message when the command /states is issued."""
    states = get_data("https://cdn-api.co-vin.in/api/v2/admin/location/states")
    result = []
    for state in states.get("states"):
        result.append(f"{state.get('state_id')} - {state.get('state_name')}")
    update.message.reply_text("\n".join(result))


def get_districts(update, context):
    """Send a message when the command /states is issued."""
    state_id = re.findall(r'[0-9]+', context.match.string)
    if len(state_id) != 1:
        raise Exception("State id missing")
    districts = get_data(f"https://cdn-api.co-vin.in/api/v2/admin/location/districts/{state_id[0]}")
    result = []
    for state in districts.get("districts"):
        result.append(f"{state.get('district_id')} - {state.get('district_name')}")
    update.message.reply_text("\n".join(result))


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(RegexHandler(r"district \d+", get_districts))
    dp.add_handler(CommandHandler("states", get_states))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
