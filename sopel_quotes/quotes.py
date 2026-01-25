# coding=utf-8
"""Sopel Quotes - A plugin for handling user added IRC quotes"""
from __future__ import annotations

from random import seed

from sopel import plugin
from sopel.config.types import StaticSection, ValidatedAttribute
from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy import create_engine, event, exc
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from sqlalchemy.pool import Pool
from sqlalchemy.sql.functions import random


Base = declarative_base()


@event.listens_for(Pool, "checkout")
def ping_connection(dbapi_connection, connection_record, connection_proxy):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SELECT 1")
    except Exception:
        raise exc.DisconnectionError()
    cursor.close()


class QuotesDB(Base):
    __tablename__ = 'quotes'
    id = Column(Integer, primary_key=True)
    key = Column(String(96))
    value = Column(Text)
    nick = Column(String(96))
    active = Column(Boolean, default=True)


class QuotesSection(StaticSection):
    db_host = ValidatedAttribute('db_host', str, default='localhost')
    db_user = ValidatedAttribute('db_user', str, default='quotes')
    db_pass = ValidatedAttribute('db_pass', str, default='')
    db_name = ValidatedAttribute('db_name', str, default='quotes')


class Quotes:
    @staticmethod
    def add(key, value, nick, bot):
        session = bot.memory['quotes_session']
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
        return res if res else False

    @staticmethod
    def match(pattern, bot):
        session = bot.memory['quotes_session']
        res = session.query(QuotesDB.key).filter(QuotesDB.key.like('%%%s%%' % pattern)).filter(QuotesDB.active == 1).all()
        session.close()
        return list(res) if res else False


def configure(config):
    config.define_section('quotes', QuotesSection)
    config.quotes.configure_setting('db_host', 'Enter ip/hostname for MySQL server:')
    config.quotes.configure_setting('db_user', 'Enter user for MySQL db:')
    config.quotes.configure_setting('db_pass', 'Enter password for MySQL db:')
    config.quotes.configure_setting('db_name', 'Enter name for MySQL db:')


def setup(bot):
    bot.settings.define_section('quotes', QuotesSection)

    db_host = bot.settings.quotes.db_host
    db_user = bot.settings.quotes.db_user
    db_pass = bot.settings.quotes.db_pass
    db_name = bot.settings.quotes.db_name

    engine = create_engine(
        f'mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}?charset=utf8mb4'
    )

    try:
        engine.connect()
    except OperationalError:
        raise

    Base.metadata.create_all(engine)
    seed()

    session = scoped_session(sessionmaker())
    session.configure(bind=engine)
    bot.memory['quotes_session'] = session


@plugin.command('quote', 'quoteadd')
@plugin.priority('high')
@plugin.example('.quote')
@plugin.example('.quote Hello')
@plugin.example('.quote Hello = World')
def get_quote(bot, trigger):
    """Add or view quotes. Use .quote <id> = <quote> to add, .quote <id> to view."""
    nick = trigger.nick

    if not trigger.group(2) or trigger.group(2) == "":
        quote = Quotes.random(bot)
        if quote:
            bot.say(f'{quote.key.upper()} = {quote.value}  [added by {quote.nick}]')
        else:
            bot.say('Unable to get random quote')
        return

    arguments = trigger.group(2).strip()
    arguments_list = arguments.split('=', 1)

    if len(arguments_list) == 1:
        quote = Quotes.search(arguments_list[0].strip(), bot)
        if quote:
            bot.say(f'{quote.key.upper()} = {quote.value}  [added by {quote.nick}]')
        else:
            bot.say("Sorry, I couldn't find anything for that.")
    else:
        key = arguments_list[0].strip()
        value = arguments_list[1].strip()

        if len(key) > 96:
            bot.say('Sorry, your key is too long.')
            return

        if len(value) > 250:
            bot.say('Sorry, your value is too long.')
            return

        quote = Quotes.add(key, value, nick, bot)

        if quote:
            bot.say('Added quote.')
        else:
            bot.say('Quote already exists.')


@plugin.command('match')
@plugin.priority('high')
@plugin.example('.match ello', "Keys Matching '*ello*' (2): (Hello, Hello World)")
def match(bot, trigger):
    """Search for keys that match the pattern."""
    if not trigger.group(2) or trigger.group(2) == "":
        bot.say('This command requires arguments.')
        return

    pattern = trigger.group(2).strip()
    responses = Quotes.match(pattern, bot)

    if responses:
        if len(responses) > 10:
            bot.say(f'Keys matching {pattern} ({len(responses)}):', trigger.nick)
            for line in [responses[x:x + 10] for x in range(0, len(responses), 10)]:
                bot.say(', '.join([i for sub in line for i in sub]), trigger.nick)
        else:
            keys = ', '.join([i for sub in responses for i in sub])
            bot.say(f'Keys matching {pattern} ({len(responses)}): ({keys})')
    else:
        bot.say(f'No responses found for {pattern}')


@plugin.command('quotedel', 'quotedelete')
@plugin.priority('high')
@plugin.example('.quotedel hello', 'Deleted quote')
def delete(bot, trigger):
    """Delete a quote by key."""
    if not trigger.group(2) or trigger.group(2) == "":
        bot.say('This command requires arguments.')
        return

    key = trigger.group(2).strip()
    Quotes.remove(key, bot)
    bot.say('Deleted quote.')
