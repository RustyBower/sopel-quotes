# coding=utf-8
# vim: set noai ts=4 sw=4:

"""
Sopel Quotes is a module for handling user added IRC quotes
"""
from random import seed
from sopel.config.types import StaticSection, ValidatedAttribute
from sopel.module import commands, example, priority
from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy import create_engine, event, exc
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import Pool
from sqlalchemy.sql.functions import random


# Define a few global variables for database interaction
Base = declarative_base()


@event.listens_for(Pool, "checkout")
def ping_connection(dbapi_connection, connection_record, connection_proxy):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SELECT 1")
    except:
        # optional - dispose the whole pool
        # instead of invalidating one at a time
        # connection_proxy._pool.dispose()

        # raise DisconnectionError - pool will try
        # connecting again up to three times before raising.
        raise exc.DisconnectionError()
    cursor.close()


# Define Quotes
class QuotesDB(Base):
    __tablename__ = 'quotes'
    id = Column(Integer, primary_key=True)
    key = Column(String(96))
    value = Column(Text)
    nick = Column(String(96))
    active = Column(Boolean, default=True)


# Define our Sopel Quotes configuration
class QuotesSection(StaticSection):
    # TODO some validation rules maybe?
    db_host = ValidatedAttribute('quotes_db_host', str, default='localhost')
    db_user = ValidatedAttribute('quotes_db_user', str, default='quotes')
    db_pass = ValidatedAttribute('quotes_db_pass', str)
    db_name = ValidatedAttribute('quotes_db_name', str, default='quotes')


# Define Quotes
class Quotes:
    @staticmethod
    def add(key, value, nick, bot):
        session = bot.memory['quotes_session']
        # Return False if quote already exists
        if Quotes.search(key, bot):
            return False
        new_quote = QuotesDB(key=key, value=value, nick=nick, active=True)
        session.add(new_quote)
        session.commit()
        session.close()
        return True

    @staticmethod
    def remove(key, bot):
        session = bot.memory['quotes_session']
        session.query(QuotesDB).filter(QuotesDB.key == key).update({'active': False})
        session.commit()
        session.close()
        return True

    @staticmethod
    def random(bot):
        session = bot.memory['quotes_session']
        res = session.query(QuotesDB).filter(QuotesDB.active == 1).order_by(random()).first()
        session.close()
        return res

    @staticmethod
    def search(key, bot):
        session = bot.memory['quotes_session']
        res = session.query(QuotesDB).filter(QuotesDB.key == key).filter(QuotesDB.active == 1).one_or_none()
        session.close()
        if res:
            return res
        else:
            return False

    @staticmethod
    def match(pattern, bot):
        session = bot.memory['quotes_session']
        res = session.query(QuotesDB.key).filter(QuotesDB.key.like('%%%s%%' % pattern)).filter(QuotesDB.active == 1).all()
        session.close()
        if res:
            return list(res)
        else:
            return False


# Walk the user through defining variables required
def configure(config):
    config.define_section('quotes', QuotesSection)
    config.quotes.configure_setting(
        'db_host',
        'Enter ip/hostname for MySQL server:'
    )
    config.quotes.configure_setting(
        'db_user',
        'Enter user for MySQL db:'
    )
    config.quotes.configure_setting(
        'db_pass',
        'Enter password for MySQL db:'
    )
    config.quotes.configure_setting(
        'db_name',
        'Enter name for MySQL db:'
    )


# Initial bot setup
def setup(bot):
    bot.config.define_section('quotes', QuotesSection)

    db_host = bot.config.quotes.db_host
    db_user = bot.config.quotes.db_user
    db_pass = bot.config.quotes.db_pass
    db_name = bot.config.quotes.db_name

    engine = create_engine('mysql+pymysql://%s:%s@%s/%s?charset=utf8mb4' % (db_user, db_pass, db_host, db_name), encoding='utf8')

    # Catch any errors connecting to MySQL
    try:
        engine.connect()
    except OperationalError:
        print("OperationalError: Unable to connect to MySQL database.")
        raise

    # Create MySQL tables
    Base.metadata.create_all(engine)

    # Initialize our RNG
    seed()

    # Set up a session for database interaction
    session = scoped_session(sessionmaker())
    session.configure(bind=engine)
    bot.memory['quotes_session'] = session


@commands('quote')
@commands('quoteadd')
@priority('high')
@example('quote')
@example('quote Hello')
@example('quote Hello = World')
def get_quote(bot, trigger):
    """.quote - Add and View Definitions"""
    nick = trigger.nick

    # If the user types .quote with no arguments, get random quote
    if not trigger.group(2) or trigger.group(2) == "":
        quote = Quotes.random(bot)
        if quote:
            bot.say('{0} = {1}  [added by {2}]'.format(quote.key.upper(), quote.value, quote.nick))
        else:
            bot.say('Unable to get random quote')
        return
    # Otherwise, lookup or set a new quote
    else:
        arguments = trigger.group(2).strip()
        argumentsList = arguments.split('=', 1)

        # Search for a specific quote
        if len(argumentsList) == 1:
            quote = Quotes.search(argumentsList[0].strip(), bot)
            if quote:
                bot.say('{0} = {1}  [added by {2}]'.format(quote.key.upper(), quote.value, quote.nick))
            else:
                bot.say('Sorry, I couldn\'t find anything for that.')
        # Set a quote
        else:
            key = argumentsList[0].strip()
            value = argumentsList[1].strip()

            # Make sure our key is less than our db field
            if len(key) > 96:
                bot.say('Sorry, your key is too long.')
                return

            # Make sure our value isn't too long (approx. 250 characters)
            if len(value) > 250:
                bot.say('Sorry, your value is too long.')
                return

            quote = Quotes.add(key, value, nick, bot)

            # If quote already exists, don't allow user to overwrite it
            if quote:
                bot.say('Added quote.')
            else:
                bot.say('Quote already exists.')


@commands('match')
@priority('high')
@example('.match ello', "Keys Matching '*ello*' (2): (Hello, Hello World)")
def match(bot, trigger):
    """.match <pattern> - Search for keys that match the pattern"""
    if not trigger.group(2) or trigger.group(2) == "":
        bot.say('This command requires arguments.')
        return
    else:
        pattern = trigger.group(2).strip()
        responses = Quotes.match(pattern, bot)

    if responses:
        # PM the message if it's > 10 responses
        if len(responses) > 10:
            bot.say('Keys matching %s (%s):' % (pattern, len(responses)), trigger.nick)
            for line in [responses[x:x + 10] for x in range(0, len(responses), 10)]:
                bot.say(', '.join([i for sub in line for i in sub]), trigger.nick)
        # Reply in channel
        else:
            bot.say('Keys matching %s (%s): (' % (pattern, len(responses)) + ', '.join([i for sub in responses for i in sub]) + ')')
    # No responses found
    else:
        bot.say('No responses found for %s' % pattern)


@commands('quotedel')
@commands('quotedelete')
@priority('high')
@example('.quotedel hello', 'Deleted quote')
@example('.quotedelete hello', 'Deleted quote')
def delete(bot, trigger):
    """.quotedelete <key> - Delete the key"""
    if not trigger.group(2) or trigger.group(2) == "":
        bot.say('This command requires arguments.')
        return
    else:
        key = trigger.group(2).strip()
        Quotes.remove(key, bot)
        bot.say('Deleted quote.')
