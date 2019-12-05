# PurpleDrop

This holds the software for PurpleDrop, a digital microfluidic device.
The hardware can be found [here](https://github.com/uwmisl/purpledrop).

To set up your Raspberry Pi properly, check out [these docs](doc/pi-setup.md).

Once the pi is set up, you should be able to install the `.deb`
packages with `sudo dpkg -i <filename>`.

At this point, you can start the `pdd` program with `sudo systemctl start pdd`.
You can use `status` instead of `start` to check on it.

Once `pdd` is running, you should be able to visit `localhost` in a
browser and control PurpleDrop.

If you'd rather use the command line, `pd-test` should be available as well.
Try `pd-test --help`.
