default: help

help:
	@echo "Use setup.py to build"
	@echo "Extra make targets available:"
	@echo " install-autostart - install autostart files (xdg, systemd)"
	@echo " install-icons - install icons"
	@echo " install - calls both of the above (but calling setup.py is still necessary)"

install-icons:
	mkdir -p $(DESTDIR)/usr/share/icons/hicolor/scalable/apps
	cp icons/eye.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qubes-eye.svg
	cp icons/eye-off.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qubes-eye-off.svg
	cp icons/black-lock.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/qubes-black-lock.svg

install-desktop:
	mkdir -p $(DESTDIR)/usr/share/applications
	cp desktop_files/disk_password_gui.desktop $(DESTDIR)/usr/share/applications/

install: install-icons install-desktop

.PHONY: clean
clean:
