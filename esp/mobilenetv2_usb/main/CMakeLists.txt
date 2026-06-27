# Адаптировано из espressif/esp-dl, examples/mobilenetv2_cls/main/CMakeLists.txt
#   https://github.com/espressif/esp-dl/blob/master/examples/mobilenetv2_cls/main/CMakeLists.txt
# Компоненты платы/LCD из исходного примера убраны: это демо получает кадры по нативному
# USB вместо камеры + дисплея, поэтому ему нужны только модель (imagenet_cls), драйвер
# USB-Serial-JTAG и высокоточный таймер.
idf_component_register(SRCS "app_main.cpp"
                       INCLUDE_DIRS "."
                       REQUIRES imagenet_cls esp_driver_usb_serial_jtag esp_timer)
