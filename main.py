#!/usr/bin/env python3
import discord
import asyncio
import re
import time
import yaml
import os
import sys
from sqlalchemy import func, create_engine
from sqlalchemy.orm import sessionmaker

from db import Base,User,Server,Trigger

def load_config(configfile):
    """Return a dict with configuration from the supplied yaml file."""
    try:
        with open(configfile, 'r') as ymlfile:
            try:
                config = yaml.load(ymlfile)
            except yaml.parser.ParserError:
                print('Could not parse config file: %s' % configfile)
                sys.exit(1)
    except IOError:
        print('Could not open config file: %s' % configfile)
        sys.exit(1)
    return config

configfile = 'config.yaml'
if os.getenv('FIKABOTTEN_CONFIG'):
    configfile = os.getenv('FIKABOTTEN_CONFIG')

config = load_config(configfile)

# Setup database
engine = create_engine(config.get('database'), echo=True)
Session = sessionmaker(bind=engine)
session = Session()
Base.metadata.create_all(engine)

# Create client
client = discord.Client()


@client.event
@asyncio.coroutine
def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

@client.event
@asyncio.coroutine
def on_message(message):
    # Stop handling messages from this bot immediately.
    if message.author == client.user:
        return

    import json
    print(json.dumps(message.raw_mentions))

    print('Recived message')

    user_id = message.author.id
    server_id = message.server.id

    print('UserID: {0}'.format(message.author.id))

    if client.user in message.mentions and 'help' in message.content:
        yield from client.send_typing(message.channel)
        yield from asyncio.sleep(4)
        yield from client.send_message(message.channel, 
"""
Jag kommer att pinga folk på fikalistan när någon pingar mig med "fika".
`@fikabotten register` - registrera dig på fikalistan.
`@fikabotten unregister` - bli borttagen ifrån fikalistan.
`@fikabotten fika` - Trigga meddelandet till alla på fikalistan.
"""
                                      )

    elif client.user in message.mentions and 'unregister' in message.content:
        print('[on_message] Removing client ID:{0} from ID:{1}'.format(user_id,
                                                                   server_id))
        u = session.query(User).filter(User.id==user_id).one_or_none()
        if u is not None:
            s = session.query(Server).filter(Server.id==server_id).one_or_none()
            if s is not None:
                s.users.remove(u)
                session.commit()
                yield from client.send_message(message.channel,
                                              "Du är nu borttagen")
            else:
                print('[on_message] unregister - server dont exist. waaat')
        else:
            print('[on_message] unregister - user dont exist')
    elif client.user in message.mentions and 'GTFO' in message.content:
        print('[on_message] Removing client ID:{0} from everywhere')
        u = session.query(User).filter(User.id==user_id).one_or_none()
        if u is not None:
            session.delete(u)
            session.commit()

    elif client.user in message.mentions and 'register' in message.content:
        print('[on_message] Adding client ID:{0} on ID:{1}'.format(user_id, server_id))
        u = session.query(User).filter(User.id==user_id).one_or_none()
        if u is None:
            u = User(id=user_id)
            session.add(u)
            print('Added user to database')

        s = session.query(Server).filter(Server.id==server_id).one_or_none()
        if s is None:
            s = Server(id=server_id)
            session.add(s)
            print('Added server to database')

        if not s in u.servers:
            u.servers.append(s)
            session.commit()
            print('Added client to server')
            yield from client.send_message(message.channel, 'Du kommer att bli'
                                           + ' pingad när det är fika på G.')
        else:
            print('But, your already registered in this server :o')
            yield from client.send_message(message.channel, 'Du är redan tillagd ')
            yield from asyncio.sleep(3)
            yield from client.send_typing(message.channel)
            yield from asyncio.sleep(1)
            yield from client.send_message(message.channel, message.author.mention + ' n00b')

    elif (client.user in message.mentions and
          len(re.findall('fika', message.content,flags=re.I)) > 0):
        print('[on_message] TIME TO GET SOME FIKA')

        h = time.localtime().tm_hour

        # Get server and user objects as u and s.
        u = session.query(User).filter(User.id==user_id).one_or_none()
        s = session.query(Server).filter(Server.id==server_id).one_or_none()

        # If hen isn't, GTFO
        if u is None:
            return

        # Do a check for odd hours of the day.
        if h < 8 or h > 23:
            yield from client.send_message(message.channel, message.author.mention + ' :middle_finger:')
            return
        elif h > 18:
            yield from client.send_message(message.channel, message.author.mention + ' Lite sent för fika nu....')
            return
        #elif h == 10 or h == 11 or h == 12:
        #    yield from client.send_message(message.channel, message.author.mention + ' Fika? Det är ju lunch...')
        #    return

        # BEGIN Anti-spam section
        # Because people are generally assholes and will probably attempt to misuse the bot.
        #

        rate_1m = (
            session.query(func.count('*'))
            .select_from(Trigger)
            .filter(Trigger.user_id==user_id)
            .filter(Trigger.server_id==server_id)
            .filter(Trigger.timestamp > time.time()-(60)) # 60s
            .scalar()
        )
        rate_g_5m = (
            session.query(func.count('*'))
            .select_from(Trigger)
            .filter(Trigger.server_id==server_id)
            .filter(Trigger.timestamp > time.time()-(5*60)) # 5*60s
            .scalar()
        )
        rate_5m = (
            session.query(func.count('*'))
            .select_from(Trigger)
            .filter(Trigger.user_id==user_id)
            .filter(Trigger.server_id==server_id)
            .filter(Trigger.timestamp > time.time()-(5*60)) # 5*60 s
            .scalar()
        )
        #rate_30m = (
        #    session.query(func.count('*'))
        #    .select_from(Trigger)
        #    .filter(Trigger.user_id==user_id)
        #    .filter(Trigger.server_id==server_id)
        #    .filter(Trigger.time > ()time.time()-(30*60)) # 5*60 s
        #    .scalar()
        #)

        rate_limit_bail = False

        # RTL-1
        if rate_g_5m >= 1:
            print('RTL-1 - silent')
            rate_limit_bail = True
        # RTL-2
        if rate_5m == 4:
            print('RTL-2 - verbose')
            rate_limit_bail = True
            yield from client.send_message(message.channel,
                                           message.author.mention +
                                           ' Förhelvete...!')
        if rate_1m == 7:
            print('RTL-3 - GTFO')
            rate_limit_bail = True
            yield from client.send_message(message.channel,
                                           message.author.mention + 
                                           ' :middle_finger:')


        session.add(Trigger(
            user_id=message.author.id,
            server_id=server_id,
            timestamp=int(time.time()) 
        ))
        # Gotta commit those changes to the DB.
        session.commit()

        if rate_limit_bail:
            return

        # END Anti-spam section
        #

        # Okej, ready for action. Vi har serverobjektet.
        if s is not None:
            fikare_db = s.users # En list med alla användare relaterade till servern.
            fikare_mentions = ""
            for fikare in fikare_db: #loopa över listan
                fikare_mentions += '<@{0.id}> '.format(fikare) # Lägg till mentions till en lång sträng.
            yield from client.send_message(message.channel, fikare_mentions +
                                           "FIKA!!") #Skrik. 

        (
            session.query(Trigger)
            .filter(Trigger.timestamp < int(time.time()-30*60))
            .delete()
        )

    elif len(re.findall('fika', message.content, flags=re.I)) > 0:
        print('[on_message] DEBUG: fika matched, but no trigger.')

    print('------')


client.run(config.get('token'))


