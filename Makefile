################################################################################
#      This file is part of OpenELEC - http://www.openelec.tv
#      Copyright (C) 2009-2013 Stephan Raue (stephan@openelec.tv)
#      Copyright (C) 2013 Lutz Fiebach (lufie@openelec.tv)
#
#  This program is dual-licensed; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with OpenELEC; see the file COPYING.  If not, see
#  <http://www.gnu.org/licenses/>.
#
#  Alternatively, you can license this library under a commercial license,
#  please contact OpenELEC Licensing for more information.
#
#  For more information contact:
#  OpenELEC Licensing  <license@openelec.tv>  http://www.openelec.tv
################################################################################

ADDON_NAME=service.libreelec.settings
ADDON_VERSION=0.8.0
DISTRONAME:=LibreELEC

BUILDDIR=build
DATADIR=/usr/share/kodi
ADDONDIR=$(DATADIR)/addons

################################################################################

all: $(BUILDDIR)/$(ADDON_NAME)

addon: $(BUILDDIR)/$(ADDON_NAME)-$(ADDON_VERSION).zip

install: $(BUILDDIR)/$(ADDON_NAME)
	mkdir -p $(DESTDIR)/$(ADDONDIR)
	cp -R $(BUILDDIR)/$(ADDON_NAME) $(DESTDIR)/$(ADDONDIR)

clean:
	rm -rf $(BUILDDIR)

uninstall:
	rm -rf $(DESTDIR)/$(ADDONDIR)/$(ADDON_NAME)

$(BUILDDIR)/$(ADDON_NAME): $(BUILDDIR)/$(ADDON_NAME)/resources
	mkdir -p $(BUILDDIR)/$(ADDON_NAME)
	cp -R src/*.png src/*.py $(BUILDDIR)/$(ADDON_NAME)
	cp COPYING $(BUILDDIR)/$(ADDON_NAME)
	cp addon.xml $(BUILDDIR)/$(ADDON_NAME)
	sed -e "s,@ADDONNAME@,$(ADDON_NAME),g" \
	    -e "s,@ADDONVERSION@,$(ADDON_VERSION),g" \
	    -e "s,@DISTRONAME@,$(DISTRONAME),g" \
	    -i $(BUILDDIR)/$(ADDON_NAME)/addon.xml
	cp changelog.txt $(BUILDDIR)/$(ADDON_NAME)

$(BUILDDIR)/$(ADDON_NAME)/resources: $(BUILDDIR)/$(ADDON_NAME)/resources/skins \
                                     $(BUILDDIR)/$(ADDON_NAME)/resources/language
	mkdir -p $(BUILDDIR)/$(ADDON_NAME)/resources
	cp -R src/resources/* $(BUILDDIR)/$(ADDON_NAME)/resources

$(BUILDDIR)/$(ADDON_NAME)/resources/skins: $(BUILDDIR)/$(ADDON_NAME)/resources/skins/Default/media/default \
                                           $(BUILDDIR)/$(ADDON_NAME)/resources/skins/Default/media/icons
	mkdir -p $(BUILDDIR)/$(ADDON_NAME)/resources/skins/Default
	cp -R skins/Default/* $(BUILDDIR)/$(ADDON_NAME)/resources/skins/Default

$(BUILDDIR)/$(ADDON_NAME)/resources/skins/Default/media/default:
	mkdir -p $(BUILDDIR)/$(ADDON_NAME)/resources/skins/Default/media/default
	cp textures/$(DISTRONAME)/*.png $(BUILDDIR)/$(ADDON_NAME)/resources/skins/Default/media/default

$(BUILDDIR)/$(ADDON_NAME)/resources/skins/Default/media/icons:
	mkdir -p $(BUILDDIR)/$(ADDON_NAME)/resources/skins/Default/media/icons
	cp icons/*.png $(BUILDDIR)/$(ADDON_NAME)/resources/skins/Default/media/icons

$(BUILDDIR)/$(ADDON_NAME)/resources/language:
	mkdir -p $(BUILDDIR)/$(ADDON_NAME)/resources/language
	cp -R language/* $(BUILDDIR)/$(ADDON_NAME)/resources/language
	sed -e "s,@DISTRONAME@,$(DISTRONAME),g" \
	    -e "s,@ROOT_PASSWORD@,$(ROOT_PASSWORD),g" \
	    -i $(BUILDDIR)/$(ADDON_NAME)/resources/language/*/*.po

$(BUILDDIR)/$(ADDON_NAME)-$(ADDON_VERSION).zip: $(BUILDDIR)/$(ADDON_NAME)
	cd $(BUILDDIR); zip -r $(ADDON_NAME)-$(ADDON_VERSION).zip $(ADDON_NAME)
