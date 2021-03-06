#!/usr/bin/env python2
"""
SC Controller - Macros

Frontier is my favorite.
"""
from __future__ import unicode_literals

from scc.actions import Action, NoAction, ButtonAction, ACTIONS, MOUSE_BUTTONS
from scc.constants import FE_STICK, FE_TRIGGER, FE_PAD
from scc.constants import LEFT, RIGHT, STICK, SCButtons


import time, logging
log = logging.getLogger("Macros")
_ = lambda x : x


class Macro(Action):
	"""
	Two or more actions executed in sequence.
	Generated when parsing ';'
	"""

	COMMAND = None
	HOLD_TIME = 0.01
	
	def __init__(self, *parameters):
		Action.__init__(self, *parameters)
		self.actions = []
		self.repeat = False
		self._active = False
		self._current = None
		self._release = None
		for p in parameters:
			if type(p) == float and len(self.actions):
				self.actions[-1].delay_after = p
			elif isinstance(p, Macro):
				self.actions += p.actions
			elif isinstance(p, Action):
				self.actions.append(p)
			else:
				self.actions.append(ButtonAction(p))
	
	
	def button_press(self, mapper):
		# Macro can be executed only by pressing button
		if len(self.actions) < 1:
			# Empty macro
			return False
		self._active = True
		if self._current is not None:
			# Already executing macro
			return False
		self._current = [] + self.actions
		self.timer(mapper)
	
	
	def timer(self, mapper):
		if self._release is None:
			# Execute next action
			self._release, self._current = self._current[0], self._current[1:]
			self._release.button_press(mapper)
			mapper.schedule(self.HOLD_TIME, self.timer)
		else:
			# Finish execited action
			self._release.button_release(mapper)
			if len(self._current) == 0 and self.repeat and self._active:
				# Repeating
				self._current = [] + self.actions
				mapper.schedule(self._release.delay_after, self.timer)
				self._release = None
			elif len(self._current) == 0:
				# Finished
				self._current = None
				self._release = None
			else:
				# Schedule for next action
				mapper.schedule(self._release.delay_after, self.timer)
				self._release = None
	
	
	def button_release(self, mapper):
		self._active = False
	
	
	def describe(self, context):
		if self.name: return self.name
		if self.repeat:
			return "repeat " + "; ".join([ x.describe(context) for x in self.actions ])
		return "; ".join([ x.describe(context) for x in self.actions ])
	
	
	def to_string(self, multiline=False, pad=0):
		lst = "; ".join([ x.to_string() for x in self.actions ])
		if self.repeat:
			return (" " * pad) + ("repeat(%s)" % (lst,))
		return (" " * pad) + lst
	
	
	def __str__(self):
		if self.repeat:
			return "<[repeat %s ]>" % ("; ".join([ str(x) for x in self.actions ]), )
		return "<[ %s ]>" % ("; ".join([ str(x) for x in self.actions ]), )
	
	__repr__ = __str__


class Repeat(Macro):
	"""
	Repeats specified action as long as physical button is pressed.
	This is actually just Macro with 'repeat' set to True
	"""
	COMMAND = "repeat"
	def __new__(cls, action):
		if not isinstance(action, Macro):
			action = Macro(action)
		action.repeat = True
		return action


class SleepAction(Action):
	"""
	Does nothing.
	If used in macro, overrides delay after itself.
	"""
	COMMAND = "sleep"
	def __init__(self, delay):
		Action.__init__(self, delay)
		self.delay = float(delay)
		self.delay_after = self.delay - Macro.HOLD_TIME
	
	def describe(self, context):
		if self.name: return self.name
		if self.delay < 1.0:
			return _("Wait %sms") % (int(self.delay*1000),)
		else:
			s = ("%0.2f" % (self.delay,)).strip(".0")
			return _("Wait %ss") % (s,)
	
	
	def to_string(self, multiline=False, pad=0):
		return (" " * pad) + "%s(%0.3f)" % (self.COMMAND, self.delay)

	
	def button_press(self, mapper): pass
	def button_release(self, mapper): pass


class PressAction(Action):
	"""
	Presses button and leaves it pressed.
	Can be used anywhere, but makes sense only with macro.
	"""
	COMMAND = "press"
	PR = _("Press")

	def __init__(self, button):
		Action.__init__(self, button)
		self.button = button


	def describe_short(self):
		""" Used in macro editor """
		if self.button in ButtonAction.SPECIAL_NAMES:
			return _(ButtonAction.SPECIAL_NAMES[self.button])
		elif self.button in MOUSE_BUTTONS:
			return _("Mouse %s") % (self.button,)
		return self.button.name.split("_", 1)[-1]
	
	
	def describe(self, context):
		if self.name: return self.name
		return self.PR + " " + self.describe_short()
	
	
	def button_press(self, mapper):
		ButtonAction._button_press(mapper, self.button)
	
	
	def button_release(self, mapper):
		# This is activated only when button is pressed
		pass


class ReleaseAction(PressAction):
	"""
	Releases button.
	Can be used anywhere, but makes sense only with macro.
	"""
	COMMAND = "release"
	PR = _("Release")
	
	def button_press(self, mapper):
		ButtonAction._button_release(mapper, self.button)


# Add macros to ACTIONS dict
for i in [ globals()[x] for x in dir() if hasattr(globals()[x], 'COMMAND') ]:
	if i.COMMAND is not None:
		ACTIONS[i.COMMAND] = i
