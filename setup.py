#!/usr/bin/env python3
""" Setup.py file """
import setuptools.command.install

setuptools.setup(
    name='disk-password-gui',
    version='0.1',
    author='Invisible Things Lab',
    author_email='marmarta@invisiblethingslab.com',
    description='Disk Password Change GUI',
    license='GPL2+',
    url='https://www.qubes-os.org/',
    packages=["disk_password_gui"],
    entry_points={
        'gui_scripts': [
            'disk-password-change = disk_password_gui.disk_password_gui:main',
        ]
    },
    package_data={'disk_password_gui': [
        "disk_password_gui_base.css",
        "disk_password_gui_light.css",
        "disk_password_gui_dark.css",
        "disk_password_gui.glade",
    ]},
)
