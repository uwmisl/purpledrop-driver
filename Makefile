
TARGET ?= armv7-unknown-linux-gnueabihf
ARCH ?= armhf
VERSION = $(shell git describe --always --dirty)
PACKAGE_NAME = purpledrop

PURPLEDROP_PACKAGE=deb/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb
PDD_SERVICE_PACKAGE=deb/pdd-service_${VERSION}_${ARCH}.deb

.PHONY: jsclient package rustrelease

rustrelease:
	cross build --release --target ${TARGET}

package: rustrelease jsclient
	cargo deb -v --target ${TARGET} --no-build --no-strip --deb-version=${VERSION}

jsclient:
	cd jsclient; npm install
	cd jsclient; npm run build
