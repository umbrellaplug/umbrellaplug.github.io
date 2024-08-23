"""
	Umbrella Add-on (Yay for new custom dialogs. thanks Peter for the help)
"""
from resources.lib.modules.control import addonIcon, getLangString as getLS, setting as getSetting, isDarkColor
from resources.lib.windows.base import BaseDialog

class OK(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.ok_label = kwargs.get('ok_label')
		self.text = kwargs.get('text')
		self.heading = kwargs.get('heading', getLS(40414))
		self.icon = kwargs.get('icon', addonIcon())
		self.customBackgroundColor = getSetting('dialogs.customcolor')
		self.customButtonColor = getSetting('dialogs.button.color')
		self.customTitleColor = getSetting('dialogs.titlebar.color')
		self.useCustomTitleColor = getSetting('dialogs.usecolortitle') == 'true'
		self.highlight_color = getSetting('sources.highlight.color')
		self.mode = getSetting('dialogs.lightordarkmode')
		self.lightcolor = 'FFF5F5F5'
		self.darkcolor = 'FF302F2F'
		self.set_properties()

	def run(self):
		self.doModal()

	def onClick(self, controlID):
		self.close()

	def onAction(self, action):
		if action in self.closing_actions: self.close()

	def set_properties(self):
		self.setProperty('ok_label', self.ok_label)
		self.setProperty('text', self.text)
		self.setProperty('heading', self.heading)
		background = {'0': self.darkcolor, '1': self.lightcolor, '2': self.customBackgroundColor}[self.mode]
		titlebar = self.customTitleColor if self.useCustomTitleColor else background
		spinner = self.highlight_color if background == titlebar else titlebar
		if self.mode not in ('0', '1'): self.mode = '0' if isDarkColor(background) else '1'
		text = self.lightcolor if self.mode == '0' else self.darkcolor
		buttontext = self.darkcolor if self.mode == '0' else self.lightcolor
		buttontextns = self.lightcolor if self.mode == '0' else self.darkcolor
		buttonnf = '33F5F5F5' if self.mode == '0' else '33302F2F'
		if self.mode == '0' and background == titlebar: titletext = self.lightcolor
		else: titletext = self.darkcolor

		self.setProperty('umbrella.backgroundColor', background)
		self.setProperty('umbrella.titleBarColor', titlebar)
		self.setProperty('umbrella.titleTextColor', titletext)
		self.setProperty('umbrella.buttonColor', self.customButtonColor)
		self.setProperty('umbrella.buttonColorNF', buttonnf)
		self.setProperty('umbrella.buttonTextColor', buttontext)
		self.setProperty('umbrella.buttonTextColorNS', buttontextns)
		self.setProperty('umbrella.spinnerColor', spinner)
		self.setProperty('umbrella.textColor', text)

class Confirm(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.selected = None
		self.default_control = kwargs.get('default_control')
		self.ok_label = kwargs.get('ok_label')
		self.cancel_label = kwargs.get('cancel_label')
		self.text = kwargs.get('text')
		self.heading = kwargs.get('heading', getLS(40414))
		self.icon = kwargs.get('icon', addonIcon())
		self.customBackgroundColor = getSetting('dialogs.customcolor')
		self.customButtonColor = getSetting('dialogs.button.color')
		self.customTitleColor =getSetting('dialogs.titlebar.color')
		self.useCustomTitleColor = getSetting('dialogs.usecolortitle') == 'true'
		self.highlight_color = getSetting('sources.highlight.color')
		self.mode = getSetting('dialogs.lightordarkmode')
		self.lightcolor = 'FFF5F5F5'
		self.darkcolor = 'FF302F2F'
		self.set_properties()

	def onInit(self):
		self.setFocusId(self.default_control)

	def run(self):
		self.doModal()
		return self.selected

	def onClick(self, controlID):
		self.selected = {10: True, 11: False}[controlID]
		self.close()

	def onAction(self, action):
		if action in self.closing_actions: self.close()

	def set_properties(self):
		self.setProperty('ok_label', self.ok_label)
		self.setProperty('cancel_label', self.cancel_label)
		self.setProperty('text', self.text)
		self.setProperty('heading', self.heading)
		background = {'0': self.darkcolor, '1': self.lightcolor, '2': self.customBackgroundColor}[self.mode]
		titlebar = self.customTitleColor if self.useCustomTitleColor else background
		spinner = self.highlight_color if background == titlebar else titlebar
		if self.mode not in ('0', '1'): self.mode = '0' if isDarkColor(background) else '1'
		text = self.lightcolor if self.mode == '0' else self.darkcolor
		buttontext = self.darkcolor if self.mode == '0' else self.lightcolor
		buttontextns = self.lightcolor if self.mode == '0' else self.darkcolor
		buttonnf = '33F5F5F5' if self.mode == '0' else '33302F2F'
		if self.mode == '0' and background == titlebar: titletext = self.lightcolor
		else: titletext = self.darkcolor

		self.setProperty('umbrella.backgroundColor', background)
		self.setProperty('umbrella.titleBarColor', titlebar)
		self.setProperty('umbrella.titleTextColor', titletext)
		self.setProperty('umbrella.buttonColor', self.customButtonColor)
		self.setProperty('umbrella.buttonColorNF', buttonnf)
		self.setProperty('umbrella.buttonTextColor', buttontext)
		self.setProperty('umbrella.buttonTextColorNS', buttontextns)
		self.setProperty('umbrella.spinnerColor', spinner)
		self.setProperty('umbrella.textColor', text)

class ProgressUmbrella(BaseDialog):
	def __init__(self, *args, **kwargs):
		BaseDialog.__init__(self, args)
		self.closed = False
		self.heading = kwargs.get('heading', getLS(40414))
		self.qr = kwargs.get('qr')
		self.artwork = kwargs.get('artwork')
		self.icon = kwargs.get('icon') or ''
		self.customBackgroundColor = getSetting('dialogs.customcolor')
		self.customButtonColor = getSetting('dialogs.button.color')
		self.customTitleColor = getSetting('dialogs.titlebar.color')
		self.useCustomTitleColor = getSetting('dialogs.usecolortitle') == 'true'
		self.highlight_color = getSetting('sources.highlight.color')
		self.mode = getSetting('dialogs.lightordarkmode')
		self.lightcolor = 'FFF5F5F5'
		self.darkcolor = 'FF302F2F'
		self.set_controls()

	def run(self):
		self.doModal()
		self.clearProperties()

	def onAction(self, action):
		if action in self.closing_actions or action in self.selection_actions:
			self.doClose()

	def doClose(self):
		self.closed = True
		self.close()
		del self

	def iscanceled(self):
		return self.closed

	def set_controls(self):
		if self.qr == 1:
			#self.getControl(200).setImage(self.icon)
			self.setProperty('umbrella.qr','1')
		else:
			self.setProperty('umbrella.qr','0')
		if self.artwork == 1:
			self.setProperty('umbrella.qr','0')
			self.setProperty('umbrella.artwork', '1')
			#self.getControl(201).setImage(self.icon)
		else:
			self.setProperty('umbrella.artwork', '0')
		self.setProperty('umbrella.heading', self.heading)
		self.setProperty('umbrella.icon', self.icon)
		background = {'0': self.darkcolor, '1': self.lightcolor, '2': self.customBackgroundColor}[self.mode]
		titlebar = self.customTitleColor if self.useCustomTitleColor else background
		spinner = self.highlight_color if background == titlebar else titlebar
		if self.mode not in ('0', '1'): self.mode = '0' if isDarkColor(background) else '1'
		text = self.lightcolor if self.mode == '0' else self.darkcolor
		buttontext = self.darkcolor if self.mode == '0' else self.lightcolor
		buttontextns = self.lightcolor if self.mode == '0' else self.darkcolor
		buttonnf = '33F5F5F5' if self.mode == '0' else '33302F2F'
		if self.mode == '0' and background == titlebar: titletext = self.lightcolor
		else: titletext = self.darkcolor

		self.setProperty('umbrella.backgroundColor', background)
		self.setProperty('umbrella.titleBarColor', titlebar)
		self.setProperty('umbrella.titleTextColor', titletext)
		self.setProperty('umbrella.buttonColor', self.customButtonColor)
		self.setProperty('umbrella.buttonColorNF', buttonnf)
		self.setProperty('umbrella.buttonTextColor', buttontext)
		self.setProperty('umbrella.buttonTextColorNS', buttontextns)
		self.setProperty('umbrella.spinnerColor', spinner)
		self.setProperty('umbrella.textColor', text)

	def update(self, percent=0, content='', icon=None):
		try:
			self.setProperty('umbrella.label', self.heading)
			self.setProperty('percent', str(percent))
			self.getControl(2001).setText(content)
			self.getControl(5000).setPercent(percent)
			if icon:
				if self.artwork == '1':
					self.getControl(201).setImage(icon)
				else:
					self.geControl(200).setImage(icon)
		except: pass