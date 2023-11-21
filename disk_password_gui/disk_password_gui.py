# -*- encoding: utf8 -*-
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2023 Marta Marczykowska-Górecka
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
import sys
import logging

import pkg_resources


import pydbus

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Gio, GdkPixbuf

logger = logging.getLogger('disk-password-gui')


def show_error(parent, title, text):
    """
    Show an error dialog. Copied from qubes-desktop-linux-manager
    :param parent: parent widget, preferably the top level window
    :param title: dialog title
    :param text: prompt text (can use pango markup)
    """
    dialog: Gtk.Dialog = Gtk.Dialog.new()
    dialog.set_modal(True)
    if parent:
        dialog.set_transient_for(parent.get_toplevel())

    button: Gtk.Button = dialog.add_button("_OK", Gtk.ResponseType.OK)
    button.set_use_underline(True)
    button.get_style_context().add_class('flat_button')
    button.get_style_context().add_class('button_save')

    dialog.set_title(title)

    content_area: Gtk.Box = dialog.get_content_area()
    content_area.get_style_context().add_class('modal_dialog')

    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    box.get_style_context().add_class('modal_contents')
    content_area.pack_start(box, False, False, 0)

    label: Gtk.Label = Gtk.Label()
    label.set_markup(text)
    label.set_line_wrap_mode(Gtk.WrapMode.WORD)
    label.set_max_width_chars(200)
    label.set_xalign(0)
    box.pack_start(label, False, False, 40)

    dialog.show_all()

    dialog.run()
    dialog.destroy()


def load_icon(icon_name: str, width: int = 24, height: int = 24):
    """Load icon from provided name, if available. If not, attempt to treat
    provided name as a path. If icon not found in any of the above ways,
    load a blank icon of specified size.
    Returns GdkPixbuf.Pixbuf.
    width and height must be in pixels.
    """
    try:
        # icon_name is a path
        return GdkPixbuf.Pixbuf.new_from_file_at_size(icon_name, width, height)
    except (GLib.Error, TypeError):
        try:
            # icon_name is a name
            image: GdkPixbuf.Pixbuf = Gtk.IconTheme.get_default().load_icon(
                icon_name, width, 0)
            return image
        except (TypeError, GLib.Error):
            # icon not found in any way
            pixbuf: GdkPixbuf.Pixbuf = GdkPixbuf.Pixbuf.new(
                GdkPixbuf.Colorspace.RGB, True, 8, width, height)
            pixbuf.fill(0x000)
            return pixbuf


def load_theme(widget: Gtk.Widget, light_theme_path: str, dark_theme_path: str):
    """
    Load a dark or light theme to current screen, based on widget's
    current (system) defaults. Taken from qubes-desktop-linux-manager.
    :param widget: Gtk.Widget, preferably main window
    :param light_theme_path: path to file with light theme css
    :param dark_theme_path: path to file with dark theme css
    """
    path = light_theme_path if is_theme_light(widget) else dark_theme_path

    screen = Gdk.Screen.get_default()
    provider = Gtk.CssProvider()
    provider.load_from_path(path)
    Gtk.StyleContext.add_provider_for_screen(
        screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def is_theme_light(widget):
    """Check if current theme is light or dark"""
    style_context: Gtk.StyleContext = widget.get_style_context()
    background_color: Gdk.RGBA = style_context.get_background_color(
        Gtk.StateType.NORMAL)
    text_color: Gdk.RGBA = style_context.get_color(
        Gtk.StateType.NORMAL)
    background_intensity = background_color.red + \
                           background_color.blue + background_color.green
    text_intensity = text_color.red + text_color.blue + text_color.green

    return text_intensity < background_intensity


class PasswordGui(Gtk.Application):
    """
    Main Gtk.Application for disk password change gui.
    """
    def __init__(self):
        """
        Simple disk password change gui.
        """
        super().__init__(application_id='org.qubesos.passwordgui')
        self.primary = False

        self.bus = pydbus.SystemBus()

        self.errors = []

        self.busy_dialog = None

    def perform_setup(self):
        """Setup all necessary widgets."""
        # pylint: disable=attribute-defined-outside-init
        self.builder = Gtk.Builder()

        self.builder.add_from_file(pkg_resources.resource_filename(
            'disk_password_gui', 'disk_password_gui.glade'))

        self.main_window: Gtk.Window = self.builder.get_object('main_window')
        self.current_pwd: Gtk.Entry = self.builder.get_object('current_pwd')
        self.new_pwd: Gtk.Entry = self.builder.get_object('new_pwd')
        self.verify_pwd: Gtk.Entry = self.builder.get_object('verify_pwd')
        self.button_ok: Gtk.Button = self.builder.get_object('button_ok')

        self.quit_action: Gio.SimpleAction = \
            Gio.SimpleAction.new('quit', None)
        self.quit_action.connect("activate", self.action_quit)
        self.main_window.add_action(self.quit_action)

        self.do_change_action: Gio.SimpleAction = \
            Gio.SimpleAction.new('change', None)
        self.do_change_action.connect("activate", self.action_do_change)
        self.main_window.add_action(self.do_change_action)

        self.do_change_action.set_enabled(False)
        self.current_pwd.connect('changed', self._on_change_text_entry)
        self.new_pwd.connect('changed', self._on_change_text_entry)
        self.verify_pwd.connect('changed', self._on_change_text_entry)

        self.current_pwd.connect('icon-press', self._make_visible)
        self.new_pwd.connect('icon-press', self._make_visible)
        self.verify_pwd.connect('icon-press', self._make_visible)
        self.current_pwd.connect('icon-release', self._make_invisible)
        self.new_pwd.connect('icon-release', self._make_invisible)
        self.verify_pwd.connect('icon-release', self._make_invisible)

        self.main_window.connect('delete-event', self.action_quit)

        self.caps_warning: Gtk.Label = self.builder.get_object(
            'caps_lock_label')

        self.busy_dialog = \
            Gtk.MessageDialog(transient_for=self.main_window,
                              modal=True,
                              text="Changing encryption password...")

        load_theme(widget=self.main_window,
                   light_theme_path=pkg_resources.resource_filename(
                       'disk_password_gui', 'disk_password_gui_light.css'),
                   dark_theme_path=pkg_resources.resource_filename(
                       'disk_password_gui', 'disk_password_gui_dark.css'))

        screen = Gdk.Screen.get_default()
        keymap = Gdk.Keymap.get_for_display(screen.get_display())
        keymap.connect('state-changed', self._keymap_state_changed)

        self._keymap_state_changed(keymap)
        self.current_pwd.grab_focus()

    def _keymap_state_changed(self, keymap: Gdk.Keymap):
        if keymap.get_caps_lock_state():
            self.caps_warning.set_text("Warning: CAPS LOCK is on!")
        else:
            self.caps_warning.set_text(" ")

    @staticmethod
    def _make_visible(widget: Gtk.Entry, icon_type, _event):
        widget.set_visibility(True)
        widget.set_icon_from_pixbuf(icon_type, load_icon('qubes-eye', 16))

    @staticmethod
    def _make_invisible(widget: Gtk.Entry, icon_type, _event):
        widget.set_visibility(False)
        widget.set_icon_from_pixbuf(icon_type, load_icon('qubes-eye-off', 16))

    def _on_change_text_entry(self, *_args):
        current_pwd = self.current_pwd.get_text()
        new_pwd = self.new_pwd.get_text()
        verify_pwd = self.verify_pwd.get_text()

        self.do_change_action.set_enabled(current_pwd and new_pwd and
                                          verify_pwd and new_pwd == verify_pwd)

        if new_pwd and new_pwd != verify_pwd:
            self.verify_pwd.get_style_context().add_class('problem')
        else:
            self.verify_pwd.get_style_context().remove_class('problem')

    def action_quit(self, *_args):
        """Quit the application."""
        self.quit()

    def _set_busy_cursor(self, state: bool = True):
        self.main_window.get_window().set_cursor(Gdk.Cursor.new_from_name(
            self.main_window.get_display(), 'progress' if state else 'default'))

    def _busy_ended(self):
        self._set_busy_cursor(False)

        if self.errors:
            show_error(self.main_window, title="Failed to change password",
                       text="Password change failed. "
                            "The following errors occurred:\n" +
                            '\n'.join(self.errors))
        else:
            self.quit()

    def _do_reencrypt(self):
        """Perform actual reencryption."""
        old_passphrase = self.current_pwd.get_text()
        new_passphrase = self.new_pwd.get_text()
        reencryptable = []
        self.errors.clear()

        try:
            disk_data = self.bus.get(".UDisks2")[
                'org.freedesktop.DBus.ObjectManager']\
                    .GetManagedObjects().items()
        except GLib.Error:
            self.errors.append("Failed to load device data.")
            disk_data = []

        for device_path, data in disk_data:
            if 'org.freedesktop.UDisks2.Encrypted' in data:
                device = self.bus.get(".UDisks2", device_path)
                if device.CleartextDevice != '/':
                    reencryptable.append(device)
        if not reencryptable:
            self.errors.append("No encrypted disks found.")

        for device in reencryptable:
            # attempt changing
            try:
                device.ChangePassphrase(old_passphrase, new_passphrase, None)
            except GLib.GError as ex:
                # pylint is confused about GLib.GError.message
                # pylint: disable=no-member
                if 'No keyslot with given passphrase found.' in ex.message:
                    self.errors.append(
                        "No matching encrypted disk found."
                        " Make sure the current password is correct.")
                else:
                    self.errors.append(ex.message)
            except Exception as ex:  # pylint: disable=broad-except
                self.errors.append(str(ex))

        self.busy_dialog.hide()
        GLib.idle_add(self._busy_ended)

    def action_do_change(self, *_args):
        """Start the password change process."""
        self.busy_dialog = \
            Gtk.MessageDialog(transient_for=self.main_window,
                              modal=True,
                              text="Changing encryption password...")
        self.busy_dialog.show()
        self._set_busy_cursor(True)

        GLib.idle_add(self._do_reencrypt)

    def do_activate(self, *args, **kwargs):
        """
        Method called whenever this program is run; it executes actual setup
        only at true first start, in other cases just presenting the main window
        to user.
        """
        if not self.primary:
            self.perform_setup()
            self.primary = True
            assert self.main_window
            self.main_window.show_all()
            self.hold()
        else:
            self.main_window.present()


def main():
    """
    Start the menu app
    """
    app = PasswordGui()
    app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
