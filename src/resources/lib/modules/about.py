# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
# Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
# Copyright (C) 2019-present Team LibreELEC (https://libreelec.tv)

import le

class about:

    ENABLED = False
    menu = {'99': {
        'name': 32196,
        'menuLoader': 'menu_loader',
        'listTyp': 'other',
        'InfoText': 705,
        }}

    @le.log_function
    def __init__(self, oeMain):
        self.oe = oeMain
        self.controls = {}

    @le.log_function
    def menu_loader(self, menuItem):
        if len(self.controls) == 0:
            self.init_controls()

    @le.log_function
    def exit_addon(self):
        self.oe.winOeMain.close()

    @le.log_function
    def init_controls(self):
        pass

    @le.log_function
    def exit(self):
        for control in self.controls:
            try:
                self.oe.winOeMain.removeControl(self.controls[control])
            except:
                pass
        self.controls = {}

    @le.log_function
    def do_wizard(self):
        self.oe.winOeMain.set_wizard_title(self.oe._(32317))
        self.oe.winOeMain.set_wizard_text(self.oe._(32318))
