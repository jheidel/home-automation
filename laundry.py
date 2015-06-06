#!/usr/bin/env python
import sys
import os
import serial
from time import time, sleep
import smtplib
from ircbot import IRCClient
from dateutil.relativedelta import relativedelta

THRESH = 1
NO_MOTION_SEC = 15
ON_THRESH = 5*60  # 5 minutes of motion required to "arm"

class SensorReader(object):

  def __init__(self):
    self.ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=5)
    self.last_value = -1

  def GetNextValue(self):
    try:
      val = ord(self.ser.read())
      self.last_value = val
      return val
    except Exception as e:
      print >> sys.stderr, 'GetNextValue exception: %s' % e.message

  def GetState(self):
    return self.GetNextValue() >= THRESH


class MachineStatus(object):

  def __init__(self):
    self.reader = SensorReader()

    self.last_active_time = time()
    self.elapsed_time = 0
    self.on_time = time()
    self.state = 'off'

    self.msg_last_time = 0

  def SetStateChangeCallback(self, callback):
    self.state_change_callback = callback

  def _StateChange(self, new_state):
    print 'State change to %s' % new_state
    if new_state == 'on':
      self.on_time = time()
      self.state_change_callback('on')
    if new_state == 'off':
      if time() - self.on_time > ON_THRESH:
        self.elapsed_time = int(time() - self.on_time)
        self.state_change_callback('done')
      else:
        self.state_change_callback('off')

  def _SetState(self, new_state):
    if self.state != new_state:
      self.state = new_state
      self._StateChange(self.state)
      
  def PrintStats(self):
    if time() < self.msg_last_time + 0.1:
      return

    msg = 'S=[%s], LV=[%d], TSLM=[%.1fs]' % (
        self.state, self.reader.last_value, time() - self.last_active_time)
    sys.stdout.write('\r%s%s' % (msg, ' '*10))
    sys.stdout.flush()
    self.msg_last_time = time()

  def Run(self):
    while True:
      if self.reader.GetState():
        self._SetState('on')
        self.last_active_time = time()
      else:
        if time() > self.last_active_time + NO_MOTION_SEC:
            self._SetState('off')

      self.PrintStats()

"""
class Notifier(object):

  def __init__(self):
    pass

  def SendMsg(self, msg):
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.starttls()
    server.login(user, pass)
    server.sendmail(email_address, 'phonenumber@txt.att.net', msg)
    server.quit()

  def Test(self):
    self.SendMsg('This is a test message.')
"""


def main():
  print '## Washing machine script thing 1.0 ##'
  #n = Notifier()

  irc = IRCClient('laundry')
  irc.start()
  irc.send('Laundry daemon is online!')

  m = MachineStatus()

  def Callback(state):
    if state == 'done':

      pieces = ['days', 'hours', 'minutes', 'seconds']
      elapsed = relativedelta(seconds=m.elapsed_time)

      time_str = ' '.join('%d%s' % (getattr(elapsed, attr), attr[0]) for attr in pieces if getattr(elapsed, attr))

      irc.send('Laundry is done! Elapsed %s' % time_str, broadcast=True)
    else:
      #irc.send('<state change to "%s">' % state)
      pass
    #n.SendMsg('Laundry done! (%.2f)' % time())

  m.SetStateChangeCallback(Callback)


  try:
    m.Run()
  except KeyboardInterrupt:
    irc.send('Laundry daemon shut down.')
    irc.stop()

if __name__ == '__main__':
  main()
