
TARGET ?= armv7-unknown-linux-gnueabihf
ARCH ?= armhf
# TODO: Need to get this version elsewhere
VERSION ?= 0.1.0
PACKAGE_NAME = purpledrop

.PHONY: jsclient package rustrelease

rustrelease:
	cross build --release --target ${TARGET}

package: rustrelease jsclient
	rm -f ${PACKAGE_NAME}_${VERSION}_${ARCH}.deb;
	fpm -a ${ARCH} -t deb -n ${PACKAGE_NAME} -v ${VERSION} -s dir \
	./target/${TARGET}/release/pdd=/usr/bin/ \
	./target/${TARGET}/release/pd-test=/usr/bin/ \
	./config/default.toml=/etc/purpledrop/ \
	./jsclient/dist/=/usr/share/purpledrop/webroot

	rm -f pdd-service_${VERSION}_${ARCH}.deb
	fpm -a ${ARCH} -t deb -n pdd-service -v ${VERSION} -s pleaserun -n pdd-service /usr/bin/pdd

jsclient:
	cd jsclient; npm install
	cd jsclient; npm run build
