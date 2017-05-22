# coding=utf-8
# vim: set noai ts=4 sw=4:

"""
Sopel Quotes is a module for handling user added IRC quotes
"""
import MySQLdb
import re
from re import sub
from random import randint, seed
from sopel.module import commands, priority, example
import sopel.web as web
import os
from collections import deque
from sopel.tools import Ddict

from sopel.config.types import StaticSection, ValidatedAttribute
from sopel.module import rule, priority
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy import create_engine, event, exc
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import Pool
from sqlalchemy.sql.expression import true
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
    value = Column(String(96))
    nick = Column(String(96))
    active = Column(Boolean)


# Define our Sopel Quotes configuration
class QuotesSection(StaticSection):
    # TODO some validation rules maybe?
    db_host = ValidatedAttribute('db_host', str, default='localhost')
    db_user = ValidatedAttribute('db_user', str, default='quotes')
    db_pass = ValidatedAttribute('db_pass', str)
    db_name = ValidatedAttribute('db_name', str, default='quotes')


# Define Bucket inventory
class Quotes:
    @staticmethod
    def add(key, value, nick, bot):
        session = bot.memory['session']
        res = session.query(QuotesDB).filter(QuotesDB.key == key).filter(Quotes.active == true()).one()
        if res:
            session.close()
            return False
        else:
            new_quote = QuotesDB(key=key, value=value, nick=nick, active=True)
            session.add(new_quote)
            session.commit()
            session.close()
            return

    @staticmethod
    def remove(key, bot):
        session = bot.memory['session']
        session.query(QuotesDB).filter(QuotesDB.key == key).update({QuotesDB.active: False})
        session.commit()
        session.close()
        return

    @staticmethod
    def random(bot):
        session = bot.memory['session']
        res = session.query(QuotesDB).order_by(random()).one()
        session.close()
        return res

    @staticmethod
    def search(key, bot):
        session = bot.memory['session']
        res = session.query(QuotesDB).filter(QuotesDB.key == key).filter(Quotes.active == true()).one()
        session.close()
        return res

    @staticmethod
    def match(pattern, bot):
        session = bot.memory['session']
        res = session.query(QuotesDB.key).filter(QuotesDB.key.like(pattern)).filter(Quotes.active == true()).all()
        session.close()
        return res


# Walk the user through defining variables required
def configure(config):
    config.define_section('quotes', QuotesSection)
    config.bucket.configure_setting(
        'db_host',
        'Enter ip/hostname for MySQL server:'
    )
    config.bucket.configure_setting(
        'db_user',
        'Enter user for MySQL db:'
    )
    config.bucket.configure_setting(
        'db_pass',
        'Enter password for MySQL db:'
    )
    config.bucket.configure_setting(
        'db_name',
        'Enter name for MySQL db:'
    )


# Initial bot setup
def setup(bot):
    bot.config.define_section('bucket', QuotesSection)

    db_host = bot.config.bucket.db_host
    db_user = bot.config.bucket.db_user
    db_pass = bot.config.bucket.db_pass
    db_name = bot.config.bucket.db_name

    engine = create_engine('mysql://%s:%s@%s/%s?charset=utf8mb4' % (db_user, db_pass, db_host, db_name), encoding='utf8')

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
    bot.memory['session'] = session


@rule('quote')
@priority('high')
@example('quote')
@example('quote Hello')
@example('quote Hello = World')
def get_quote(bot, trigger):
    """
    .quote - Add and View Definitions
    """
    item_key = None
    item_value = None
    nick = trigger.nick

    # If the user types .quote with no arguments, get random quote
    if not trigger.group(2) or trigger.group(2) == "":
        quote = Quotes.random(bot)
        bot.say('{0} = {1}  [added by {2}]'.format(quote['key'].upper(), quote['value'], quote['nick']))
        return
    # Otherwise, lookup or set a new quote
    else:
        arguments = trigger.group(2).strip()
        argumentsList = arguments.split('=', 1)

        # Search for a specific quote
        if len(argumentsList) == 1:
            quote = Quotes.search(argumentsList[0].strip())
            if quote:
                bot.say('{0} = {1}  [added by {2}]'.format(quote['key'].upper(), quote['value'], quote['nick']))
            else:
                bot.say('Sorry, I couldn\'t find anything for that.')
        # Set a quote
        else:
            key = argumentsList[0].strip()
            value = argumentsList[1].strip()

            # Make sure our key is less than our db field
            if len(item_key) > 96:
                bot.say('Sorry, your key is too long.')
                return

            quote = Quotes.add(key, value, nick, bot)

            # If quote already exists, don't allow user to overwrite it
            if quote:
                bot.say('Added quote.')
            else:
                bot.say('Quote already exists.')


@commands('match')
@priority('high')
@example('.match ello', "Keys Matching '*ello*': (Hello, Hello World)")
def match(bot, trigger):
    """
    .match <pattern> - Search for keys that match the pattern
    """
    if not trigger.group(2) or trigger.group(2) == "":
        bot.say('This command requires arguments.')
        return
    else:
        pattern = trigger.group(2).strip()
        responses = Quotes.match(pattern, bot)

        if responses is None:
            bot.say('No responses found for %s' % pattern)
        else:
            bot.say('Keys matching %s: (' % pattern + ', '.join(responses) + ')')


@commands('delete')
@priority('high')
@example('.delete hello', 'Deleted quote')
def delete(bot, trigger):
    """
    .delete <key> - Delete the key
    """
    if not trigger.group(2) or trigger.group(2) == "":
        bot.say('This command requires arguments.')
        return
    else:
        key = trigger.group(2).strip()
        res = Quotes.remove(key, bot)
        bot.say('Deleted quote.')

if __name__ == '__main__':
    print(__doc__.strip())
