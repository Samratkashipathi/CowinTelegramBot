import logging
import re

import prettytable as pt
import requests
from telegram import ParseMode
from telegram.ext import Updater, CommandHandler, RegexHandler
from telegram_bot_pagination import InlineKeyboardPaginator, InlineKeyboardButton

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

    table = pt.PrettyTable(["State ID", "State Name"])

    for state in states.get("states"):
        table.add_row([state.get('state_id'), state.get('state_name')])

    update.message.reply_text(f'<pre>{table}</pre>', parse_mode=ParseMode.HTML)


def get_districts(update, context):
    """Send a message when the command /states is issued."""
    state_id = re.findall(r'[0-9]+', context.match.string)
    if len(state_id) != 1:
        raise Exception("State id missing")
    districts = get_data(f"https://cdn-api.co-vin.in/api/v2/admin/location/districts/{state_id[0]}")

    table = pt.PrettyTable(["District ID", "District Name"])

    for state in districts.get("districts"):
        table.add_row([state.get('district_id'), state.get('district_name')])

    update.message.reply_text(f'<pre>{table}</pre>', parse_mode=ParseMode.HTML)


def get_available_slots_by_pin(update, context):
    """Send a message when the command /find_by_pin is issued."""
    if len(context.match.string.split()) != 3:
        raise Exception("Pin code or Date missing")

    date, pin_code = context.match.string.split()[1], context.match.string.split()[2]
    if not pin_code or not date:
        raise Exception("Pin code or Date missing")

    availability = get_data(
        f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByPin?pincode={pin_code}&date={date}")

    slots = availability.get("sessions")

    if len(slots) < 1:
        raise Exception("No slots available")

    required_keys = ["name", "vaccine", "slots", "min_age_limit", "available_capacity"]

    table = pt.PrettyTable(required_keys)

    for slot in slots:
        table.add_row([slot[key] for key in required_keys])

    update.message.reply_text(f'<pre>{table}</pre>', parse_mode=ParseMode.HTML)


def get_available_slots_by_district_id_helper(date, district_id):
    """Send a message when the command /find_by_pin is issued."""

    availability = get_data(
        f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByDistrict?district_id={district_id}&date={date}")

    slots = availability.get("sessions")

    return slots


def get_available_slots_by_district_id(update, context):
    """Send a message when the command /find_by_pin is issued."""
    if len(context.match.string.split()) != 3:
        raise Exception("District ID or Date missing")

    date, district_id = context.match.string.split()[1], context.match.string.split()[2]
    if not district_id or not date:
        raise Exception("District ID or Date missing")

    slots = get_available_slots_by_district_id_helper(date=date, district_id=get_available_slots_by_district_id_helper)

    required_keys = ["name", "vaccine", "slots", "min_age_limit", "available_capacity"]

    table = pt.PrettyTable(required_keys)

    for slot in slots[:5]:
        table.add_row([slot[key] for key in required_keys])

    paginator = InlineKeyboardPaginator(
        len(slots[:5]),
        data_pattern='character#{page}'
    )

    update.message.reply_text(
        text=f'<pre>{table}</pre>',
        reply_markup=paginator.markup,
        parse_mode=ParseMode.HTML
    )


def characters_page_callback(update, context):
    if len(context.match.string.split()) != 3:
        raise Exception("District ID or Date missing")

    date, district_id = context.match.string.split()[1], context.match.string.split()[2]
    if not district_id or not date:
        raise Exception("District ID or Date missing")

    query = update.callback_query

    query.answer()

    page = int(query.data.split('#')[1])

    slots = get_available_slots_by_district_id_helper(date, district_id)

    paginator = InlineKeyboardPaginator(
        len(slots[page:page + 5]),
        current_page=page,
        data_pattern='character#{page}'
    )

    paginator.add_after(InlineKeyboardButton('Go back', callback_data='back'))

    required_keys = ["name", "vaccine", "slots", "min_age_limit", "available_capacity"]

    table = pt.PrettyTable(required_keys)

    for slot in slots[:5]:
        table.add_row([slot[key] for key in required_keys])

    update.message.reply_text(
        text=f'<pre>{table}</pre>',
        reply_markup=paginator.markup,
        parse_mode=ParseMode.HTML
    )


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
    dp.add_handler(CommandHandler("states", get_states))
    dp.add_handler(RegexHandler(r"district \d+", get_districts))
    dp.add_handler(RegexHandler(r"find_by_pin [\d]{2}-[\d]{2}-[\d]{4} \d+", get_available_slots_by_pin))
    dp.add_handler(RegexHandler(r"find_by_district_id [\d]{2}-[\d]{2}-[\d]{4} \d+", get_available_slots_by_district_id))

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
