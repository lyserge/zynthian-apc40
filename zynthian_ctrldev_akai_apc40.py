#!/usr/bin/python3
# -*- coding: utf-8 -*-
#******************************************************************************
# ZYNTHIAN PROJECT: Zynthian Control Device Driver
#
# Zynthian Control Device Driver for "Akai APC40 (Mk1)"
#
# Copyright (C) 2023 lyserge <github@dashalx.co.uk>
#
#******************************************************************************
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
#******************************************************************************
import logging

# Zynthian specific modules
from zyngui.zynthian_ctrldev_manager import zynthian_ctrldev_zynpad
from zyncoder.zyncore import lib_zyncore
from zynlibs.zynseq import zynseq

# All the launch button colour states
COLOUR_OFF = 0
COLOUR_GREEN = 1
COLOUR_GREEN_BLINK = 2
COLOUR_RED = 3
COLOUR_RED_BLINK = 4
COLOUR_ORANGE = 5
COLOUR_ORANGE_BLINK = 6

# Launch grid notes all fall between these values, which determine
# the y coordinates of button presses on the grid.
PAD_NOTE_MIN = 0x35
PAD_NOTE_MAX = 0x39

PAD_WIDTH = 8
PAD_HEIGHT = 5

# ------------------------------------------------------------------------------------------------------------------
# Akai APC40 (Mk1)
# ------------------------------------------------------------------------------------------------------------------

class zynthian_ctrldev_akai_apc40(zynthian_ctrldev_zynpad):

    dev_zynpad = True		# Can act as a zynpad trigger device
    dev_ids = ['Akai_APC40', 'Akai_APC40_MIDI_1']

    def __init__(self):
        super().__init__()
        self.zynpad = self.zyngui.screens["zynpad"]

    # It *SHOULD* be implemented by child class
    def refresh_zynpad_bank(self):
        # TODO: implement this
        pass

    def decode_channel(self, event):
        # The APC40 launch grid splits its columns along MIDI channels 1-8,
        # so we need to know which channel an event was sent on to determine
        # the x coordinate of the button that was pressed
        status_byte = (event >> 16) & 0xFF
        channel = (status_byte & 0x0F) + 1
        return channel

    def midi_event(self, event):
        logging.debug("APC40 MIDI handler => {}".format(event))
        event_type = (event & 0xF00000) >> 20
        idev = (event & 0xFF000000) >> 24
        channel = self.decode_channel(event)
        note = None

        # note press event
        if event_type == 0x9:
            note = (event >> 8) & 0x7F
            val = event & 0x7F
            logging.debug(f"Event type: {event_type}; idev: {idev}; channel: {channel}; note: {note}; val: {val}")

        # launch pad button press
        if (note and channel >= 1 and channel <= 8):
            x = channel - 1
            y = note - PAD_NOTE_MIN
            pad = self.zynpad.get_pad_from_xy(x, y)
            if pad >= 0:
                self.zyngui.zynseq.libseq.togglePlayState(self.zynpad.bank, pad)
            return True

    def update_pad(self, pad, state, mode):
        logging.debug("Updating APC40 pad {}".format(pad))
        col, row = self.zynpad.get_xy_from_pad(pad)
        if (col >= PAD_WIDTH or row >= PAD_HEIGHT):
            logging.debug(f"Pad position {col}{row} out of bounds for APC40")
            return False

        channel = col
        note = PAD_NOTE_MIN + row
        group = self.zyngui.zynseq.libseq.getGroup(self.zynpad.bank, pad)

        # The velocity value in messages sent to the pad is used to set button colour state
        try:
            if mode == 0:
                velocity = COLOUR_RED
            elif state == zynseq.SEQ_STOPPED:
                velocity = COLOUR_RED
            elif state == zynseq.SEQ_PLAYING:
                velocity = COLOUR_GREEN
            elif state == zynseq.SEQ_STOPPING:
                velocity = COLOUR_ORANGE
            elif state == zynseq.SEQ_STARTING:
                velocity = COLOUR_GREEN_BLINK
            else:
                velocity = COLOUR_RED
        except:
            velocity = COLOUR_RED

        logging.debug("Lighting PAD {}, group {} => {}, {}, {}".format(pad, group, channel, note, velocity))
        lib_zyncore.dev_send_note_on(self.idev, channel, note, velocity)
