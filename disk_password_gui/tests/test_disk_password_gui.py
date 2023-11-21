# -*- encoding: utf8 -*-
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2022 Marta Marczykowska-Górecka
#                               <marmarta@invisiblethingslab.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 2.1 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with this program; if not, see <http://www.gnu.org/licenses/>.

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=protected-access

from ..disk_password_gui import PasswordGui
import subprocess

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, GLib


def test_password_gui_good_values():
    app = PasswordGui()
    # do not call do_activate - it will make Gtk confused and, in case
    # of errors, spawn an entire screenful of windows
    app.perform_setup()

    # the ok button should not be sensitive
    assert not app.button_ok.get_sensitive()

    # enter correct data
    app.current_pwd.set_text('oldpwd')
    app.new_pwd.set_text('newpwd')
    app.verify_pwd.set_text('newpwd')

    # the ok button should be sensitive
    assert app.button_ok.get_sensitive()


def test_password_gui_bad_values():
    app = PasswordGui()
    # do not call do_activate - it will make Gtk confused and, in case
    # of errors, spawn an entire screenful of windows
    app.perform_setup()

    # the ok button should not be sensitive
    assert not app.button_ok.get_sensitive()

    # enter wrong data
    app.current_pwd.set_text('oldpwd')
    app.new_pwd.set_text('newpwd')
    app.verify_pwd.set_text('wrongpwd')

    # the ok button should not be sensitive
    assert not app.button_ok.get_sensitive()

    # correct error
    app.verify_pwd.set_text('newpwd')

    # the ok button should be sensitive
    assert app.button_ok.get_sensitive()

    # make an error
    app.new_pwd.set_text('wrongpwd')

    # the ok button should not be sensitive
    assert not app.button_ok.get_sensitive()

    app.new_pwd.set_text('newpwd')

    assert app.button_ok.get_sensitive()

    app.current_pwd.set_text('')

    assert not app.button_ok.get_sensitive()


def test_password_gui_caps():
    app = PasswordGui()
    # do not call do_activate - it will make Gtk confused and, in case
    # of errors, spawn an entire screenful of windows
    app.perform_setup()

    assert app.caps_warning.get_text() == ' '

    # press Caps Lock
    subprocess.call(['xdotool', 'key', 'Caps_Lock'])

    while Gtk.events_pending():
        Gtk.main_iteration_do(blocking=True)

    # Houston, we have a warning
    assert app.caps_warning.get_text() != ' '

    # press Caps Lock
    subprocess.call(['xdotool', 'key', 'Caps_Lock'])

    while Gtk.events_pending():
        Gtk.main_iteration_do(blocking=True)

    assert app.caps_warning.get_text() == ' '

# Życzenia NADJA
class MockObj:
    def __init__(self, data):
        self.data = data

    def ChangePassphrase(self, old, new, options):
        if options is not None:
            raise GLib.GError
        if old == self.Passphrase:
            self.data['org.freedesktop.UDisks2.Encrypted']['Passphrase'] = new
            return
        raise GLib.GError("No keyslot with given passphrase found.")

    def __getattr__(self, item):
        try:
            return self.data[item]
        except KeyError:
            for val in self.data.values():
                if isinstance(val, dict):
                    if item in val:
                        return val[item]
        raise GLib.GError("No keyslot with given passphrase found.")


class MockObjManager:
    def __init__(self, data):
        self.data = data

    def GetManagedObjects(self):
        return self.data


class MockBus:
    def __init__(self, data):
        self.data = data

    def get(self, name: str, obj_path=None):
        if not name.endswith('.UDisks2'):
            raise KeyError
        if not obj_path:
            return {
                'org.freedesktop.DBus.ObjectManager': MockObjManager(self.data)}
        return MockObj(self.data[obj_path])


def test_password_gui_do_change():
    normal_setup = {
        '/org/freedesktop/UDisks2/block_devices/dm_2d0': {
            'org.freedesktop.UDisks2.Block': {}},
        '/org/freedesktop/UDisks2/block_devices/xvdb': {
             'org.freedesktop.UDisks2.Filesystem': {},
             'org.freedesktop.UDisks2.Block': {}},
        '/org/freedesktop/UDisks2/block_devices/xvdc3': {
             'org.freedesktop.UDisks2.Partition': {},
             'org.freedesktop.UDisks2.Block': {},
             'org.freedesktop.UDisks2.Encrypted': {
                 'ChildConfiguration': [], 'HintEncryptionType': '',
                 'MetadataSize': 1234,
                 'Passphrase': 'oldpwd',  # mock passphrase
                 'CleartextDevice':
                     '/org/freedesktop/UDisks2/block_devices/dm_2d0'}},
        '/org/freedesktop/UDisks2/block_devices/dm_2d5': {
            'org.freedesktop.UDisks2.Filesystem': {},
            'org.freedesktop.UDisks2.Block': {}},
        '/org/freedesktop/UDisks2/block_devices/xvda3': {
            'org.freedesktop.UDisks2.Filesystem': {},
            'org.freedesktop.UDisks2.Partition': {},
            'org.freedesktop.UDisks2.Block': {}}}

    mock_bus = MockBus(normal_setup)

    app = PasswordGui()
    app.bus = mock_bus
    # do not call do_activate - it will make Gtk confused and, in case
    # of errors, spawn an entire screenful of windows
    app.perform_setup()

    app.current_pwd.set_text('oldpwd')
    app.new_pwd.set_text('newpwd')
    app.verify_pwd.set_text('newpwd')

    # to avoid messing with threads, run the reencrypt function directly
    app._do_reencrypt()
    assert not app.errors
    assert app.bus.data['/org/freedesktop/UDisks2/block_devices/xvdc3'][
               'org.freedesktop.UDisks2.Encrypted']['Passphrase'] == 'newpwd'


def test_password_gui_do_change_wrongpwd():
    normal_setup = {
        '/org/freedesktop/UDisks2/block_devices/dm_2d0': {
            'org.freedesktop.UDisks2.Block': {}},
        '/org/freedesktop/UDisks2/block_devices/xvdb': {
             'org.freedesktop.UDisks2.Filesystem': {},
             'org.freedesktop.UDisks2.Block': {}},
        '/org/freedesktop/UDisks2/block_devices/xvdc3': {
             'org.freedesktop.UDisks2.Partition': {},
             'org.freedesktop.UDisks2.Block': {},
             'org.freedesktop.UDisks2.Encrypted': {
                 'ChildConfiguration': [], 'HintEncryptionType': '',
                 'MetadataSize': 1234,
                 'Passphrase': 'otherpwd',  # mock passphrase
                 'CleartextDevice':
                     '/org/freedesktop/UDisks2/block_devices/dm_2d0'}},
        '/org/freedesktop/UDisks2/block_devices/dm_2d5': {
            'org.freedesktop.UDisks2.Filesystem': {},
            'org.freedesktop.UDisks2.Block': {}},
        '/org/freedesktop/UDisks2/block_devices/xvda3': {
            'org.freedesktop.UDisks2.Filesystem': {},
            'org.freedesktop.UDisks2.Partition': {},
            'org.freedesktop.UDisks2.Block': {}}}

    mock_bus = MockBus(normal_setup)

    app = PasswordGui()
    app.bus = mock_bus
    # do not call do_activate - it will make Gtk confused and, in case
    # of errors, spawn an entire screenful of windows
    app.perform_setup()

    app.current_pwd.set_text('oldpwd')
    app.new_pwd.set_text('newpwd')
    app.verify_pwd.set_text('newpwd')

    # to avoid messing with threads, run the reencrypt function directly
    app._do_reencrypt()
    assert 'No matching encrypted disk found' in app.errors[0]
    assert len(app.errors) == 1


def test_password_gui_do_complex():
    normal_setup = {
        '/org/freedesktop/UDisks2/block_devices/dm_2d0': {
            'org.freedesktop.UDisks2.Block': {}},
        '/org/freedesktop/UDisks2/block_devices/xvdb': {
             'org.freedesktop.UDisks2.Filesystem': {},
             'org.freedesktop.UDisks2.Block': {}},
        '/org/freedesktop/UDisks2/block_devices/xvdc3': {
             'org.freedesktop.UDisks2.Partition': {},
             'org.freedesktop.UDisks2.Block': {},
             'org.freedesktop.UDisks2.Encrypted': {
                 'ChildConfiguration': [], 'HintEncryptionType': '',
                 'MetadataSize': 1234,
                 'Passphrase': 'oldpwd',  # mock passphrase
                 'CleartextDevice':
                     '/org/freedesktop/UDisks2/block_devices/dm_2d0'}},
        '/org/freedesktop/UDisks2/block_devices/dm_2d5': {
            'org.freedesktop.UDisks2.Filesystem': {},
            'org.freedesktop.UDisks2.Block': {},
            'org.freedesktop.UDisks2.Encrypted': {
                'ChildConfiguration': [], 'HintEncryptionType': '',
                'MetadataSize': 1234,
                'Passphrase': 'oldpwd',  # mock passphrase
                'CleartextDevice':
                    '/'}},
        '/org/freedesktop/UDisks2/block_devices/xvda3': {
            'org.freedesktop.UDisks2.Filesystem': {},
            'org.freedesktop.UDisks2.Partition': {},
            'org.freedesktop.UDisks2.Block': {}}}

    mock_bus = MockBus(normal_setup)

    app = PasswordGui()
    app.bus = mock_bus
    # do not call do_activate - it will make Gtk confused and, in case
    # of errors, spawn an entire screenful of windows
    app.perform_setup()

    app.current_pwd.set_text('oldpwd')
    app.new_pwd.set_text('newpwd')
    app.verify_pwd.set_text('newpwd')

    # to avoid messing with threads, run the reencrypt function directly
    app._do_reencrypt()
    assert not app.errors
    assert app.bus.data['/org/freedesktop/UDisks2/block_devices/dm_2d5'][
               'org.freedesktop.UDisks2.Encrypted']['Passphrase'] == 'oldpwd'
    assert app.bus.data['/org/freedesktop/UDisks2/block_devices/xvdc3'][
               'org.freedesktop.UDisks2.Encrypted']['Passphrase'] == 'newpwd'
