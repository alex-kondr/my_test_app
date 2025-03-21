# import usb
# from usb.backend import libusb1

# back = libusb1.get_backend()
# dev_list = usb.core.find(find_all=True, backend=back)
# # len(dev_list)
# for d in dev_list:
#     print(d)#,d.iManufacturer))
#     # print(usb.util.get_string(d,128,d.iProduct))
#     print(d.idProduct, d.idVendor)

# my_list = [6, 2, 3, 4, 5]

# def test_iter(items: list):
#     for item in items:
#         yield item


# # print(next(test_iter(my_list)))
# my_iter = test_iter(my_list)
# print(next(my_iter))
# print(next(my_iter))
# print(next(my_iter))
# print(next(my_iter))
# print(next(test_iter(my_list)))
# print(next(test_iter(my_list)))
# print(next(test_iter(my_list)))
# print(next(test_iter(my_list)))
# print(next(test_iter(my_list)))

# print(next(my_list))
# print(next(my_list))
# print(next(my_list))
# print(next(my_list))
# print(next(my_list))
# print(next(my_list))