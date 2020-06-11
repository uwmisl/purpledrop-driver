.PHONY: jsclient

jsclient:
	cd jsclient; yarn install
	cd jsclient; yarn build
	cd jsclient/dist; tar -zcf ../../purpledrop/frontend-dist.tar.gz *
