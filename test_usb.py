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


# def is_prime(n: int) -> bool:
#     i = 2
#     if n < 2:
#         return False

#     while i < n ** 0.5:
#         if n % i == 0:
#             print(i)
#             return False
#         i += 1
#     return True


# print(is_prime(2000))

# PC & Gaming|Gaming|Playstation 5
# PC & Gaming|Souris PC|Souris gamer
# cats = 'PC & Gaming|Gaming|Playstation 5'.split('|')

# category = ''
# for cat in cats:
#     if not (any([cat_ for cat_ in cat.split() if cat_ in category])):
#         category += cat + '|'
# print(category.strip('|'))

a = """Materiaal aangename touch 
Voldoet aan de eigenschappen"""

ass = a.splitlines()
print(ass)
print('\n' in a)
print(a.split('\n'))