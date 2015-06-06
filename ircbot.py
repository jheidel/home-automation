"""IRC bot framework for household IRC clients.

Jeff Heidel 2015.
"""
import irclib
from threading import Thread, Event
from time import sleep


class IRCClient(Thread):

  def __init__(self, nickname, server='192.168.1.2', port=6667,
               channel='#local'):
    super(IRCClient, self).__init__()

    self.nickname = nickname
    self.server = server
    self.port = port
    self.channel = channel
    self.irc = irclib.IRC()
    self.message_queue = []

    self.names = []
    self.names_received = Event()

    self.killed = False

  def _names_handler(self, conn, event):
    self.names[:] = sorted(event.arguments()[2].split(' '))
    self.names_received.set()

  def list_names(self):
    self.names_received.clear()
    self.conn.names()
    self.names_received.wait(5)
    return self.names

  def connect_and_join(self):
    self.conn = self.irc.server().connect(
        server=self.server,
        port=self.port,
        nickname=self.nickname)
    self.conn.join(self.channel)

    # Add handlers
    self.conn.add_global_handler('namreply', self._names_handler)

  def start(self):
    self.connect_and_join()
    super(IRCClient, self).start()

  def stop(self):
    self.killed = True

  def __enter__(self):
    self.start()

  def __exit__(self, *exc_args):
    self.stop()

  def send(self, msg, broadcast=False):
    if broadcast:
      msg += ' [%s]' % ' '.join(self.list_names())
    self.message_queue.append(msg)

  def flush_message_queue(self):
    while self.message_queue:
      self.conn.privmsg(self.channel, self.message_queue.pop(0))

  def shutdown(self):
    # Cleans up state
    self.conn.quit()
    self.irc.disconnect_all()

  def run(self):
    while not self.killed:
      self.irc.process_once(timeout=0.1)

      if self.conn.is_connected():
        self.flush_message_queue()
      else:
        try:
          self.connect_and_join()
        except irclib.ServerConnectionError:
          sleep(0.1)

    self.shutdown()
