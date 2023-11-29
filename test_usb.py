import usb
from usb.backend import libusb1

back = libusb1.get_backend()
dev_list = usb.core.find(find_all=True, backend=back)
# len(dev_list)
for d in dev_list:
    print(d)#,d.iManufacturer))
#     # print(usb.util.get_string(d,128,d.iProduct))
#     print(d.idProduct, d.idVendor)