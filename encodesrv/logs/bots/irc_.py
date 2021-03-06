"""IRC bot handler for encodesrv.

Author: Robert Walker <robert.walker@ystv.co.uk> 2015
"""

import irc.bot
import irc.strings
import logging
import time
import threading

from . import common
from ..messages import Message_enum

# Turn off the irc module log.
logging.getLogger('irc').setLevel(logging.CRITICAL)
logger = logging.getLogger(__name__)

class IRC_bot(irc.bot.SingleServerIRCBot):
    
    """Class that does the main talking to IRC."""
    
    def __init__(self, parent = None, channel = "", nick = "", server = "", ident_pass = "", port=6667, **kwargs):
        
        """Create the bot.
        
        Arguments:
            channel (string): Channel for the bot to live in.
            nick (string): Bot's nick.
            server (string): IRC server to connect to.
            port (int): Port to connect to the server on.
            ident_pass (string): Password to identify to chanserv with. 
            
        Returns:
            IRC_bot instance.
        """
        
        assert type(channel) == str
        assert type(ident_pass) == str
        assert type(nick) == str
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nick, nick)
        self.channel = channel
        self.joined = False
        self.parent = parent
        self.ident_pass = ident_pass 
        
    def _on_join(self, c, e):
        
        """Triggered on a channel join."""
        
        super(IRC_bot, self)._on_join(c, e)
        self.joined = True
        self.send_msg("identify " + self.ident_pass, "nickserv")

    def on_nicknameinuse(self, c, e):
        
        """Triggered on a nickname change."""
        
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        
        """Triggered on server join."""
        
        c.join(self.channel)

    def on_privmsg(self, c, e):
        
        """Triggered on a private (query) message."""
        
        self.do_command(e, e.arguments[0], True)

    def on_pubmsg(self, c, e):
        
        """Triggered on a channel message."""
        
        a = e.arguments[0].split(":", 1)
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(self.connection.get_nickname()):
            self.do_command(e, a[1].strip())
        return

    def do_command(self, e, cmd, private = False):
        
        """Work out how to respond to a command.
        
        Arguments:
            private (bool): Was the command a query (True) or channel (False) message.
            
        Returns:
            None.
        """
        
        nick = e.source.nick
        
        daemon = self.parent.parent
        enum = Message_enum
        form_msg = common.form_msg

        if cmd == "status":
            msg = form_msg(enum.status, daemon)
        else:
            msg = form_msg(enum.unknown_cmd, daemon)
            
        if private:
            args = {"msg": msg, "channel": nick}
        else:
            args = {"msg": nick + ": " + msg}
        
        self.send_msg(**args)
            
    def is_joined(self):
        
        return self.joined
    
    def send_msg(self, msg = "", channel = None):
        
        if channel is None:
            channel = self.channel
        self.connection.privmsg(channel, msg)

class Bot_thread(threading.Thread):
    
    """Thread to host the bot, cause it's blocking."""
    
    def __init__(self, bot):
        
        super(Bot_thread, self).__init__()
        self.bot = bot
        
    def run(self):
        
        """Run bot, run!"""
        
        self.bot.start()

class Encode_irc(logging.Handler):
    
    def __init__(self, parent, **kwargs):
        
        super(Encode_irc, self).__init__()
        self.parent = parent
        self.bot = IRC_bot(self, **kwargs)
        self.thread = Bot_thread(self.bot)
        self.thread.start()
        while not self.bot.is_joined():
            time.sleep(0.1)
        logger.info("Connected to IRC.")
    
    def is_joined(self):
        
        return self.bot.is_joined()
        
    def emit(self, record):
        
        """What do we do with a log message?"""
        
        self.send_msg(record.getMessage())
        
    def send_msg(self, msg):
        
        """Make it the bots problem!"""
        
        self.bot.send_msg(msg)
