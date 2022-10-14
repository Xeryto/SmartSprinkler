import sensor, image, time, math, pyb


# Класс-обёртка для удобного управления направлением и стартом/стопом двигателя. Лучше чем выдавать high() и low() на пины и помнить за что они отвечают
class Motor:
    # КОнструктор, нужно будет указать в виде строки названия пинов DIR и EN
    def __init__(self, dir_pin, enable_pin):
        self.direction = pyb.Pin(dir_pin, pyb.Pin.OUT_PP)
        self.enable = pyb.Pin(enable_pin, pyb.Pin.OUT_PP)

    # Старт мотора
    def run(self):
        self.enable.low()

    # Стоп мотора
    def stop(self):
        self.enable.high()

    # Направление - вправо. Может быть нужно поменять при неверном подключении обмоток. Тогда поменять high и low местами
    def right(self):
        self.direction.low()

    # Направление - влево. Может быть нужно поменять при неверном подключении обмоток
    def left(self):
        self.direction.high()


def real_freq(delta):
    if delta == 0:  # Избегаем деления на 0
        delta = 1

    # Расчёт точной частоты
    freq = math.ceil((10000 / (160/abs(delta)))/100)*100

    return freq


# Динамическая нелинейная частота с несколькими шагами
def frequency_steps(delta):
    freq = real_freq(delta)

    # Границы частот
    # thrs = (4000, 4500, 5000, 5500, 6000, 6500, 7000, 7500, 8000, 8500, 9000, 9500, 10000)
    thrs = (4000, 5000, 6000, 7000, 8000, 9000, 10000)
    # Итоговые частоты по возрастанию. Надо менять в соответствии с границами
    # f_steps = (4000, 4500, 5000, 5500, 6000, 6500, 7000, 7500, 8000, 8500, 9000, 9500)
    f_steps = (4000, 5000, 6000, 7000, 8000, 9000)
    # Вспомогательный коэфф, чтобы удобнее двигать f_steps массово
    f_coeff = 0
    f_steps_coeff = -1000

    # перебор границ thrs по возрастанию, вычисляем в какой диапазон попадает freq
    for i, t in enumerate(thrs):
        if freq <= t + f_coeff:
            # попали в диапазон, индекс списка шагов минус 1
            index = i - 1
            if index < 0:
                index = 0

            # print('in={}, out={}'.format(freq, f_steps[index] + f_steps_coeff))
            return f_steps[index] + f_steps_coeff

    # f больше максимума? надо вернуть последнюю максимальную частоту
    return f_steps[-1] + f_steps_coeff

# Промежуточная частота
def intermediate_freq(current_freq, previous_freq):
    average = math.floor(((current_freq + previous_freq) / 2)/500)*500  # Среднее арифметическое

    return average


# MOTOR -----
motor = Motor("P8", "P9")
PWM_pin = "P4"



pause = 0  # Пауза при отсутствии определении кадров
border = 30  # Размер мёртвой зоны в пикселях. Мёртвая зона = +-30, то есть 60
fps = 40  # Как долго игнорировать отсутствие метки в кадре. При съёмке 40 к/с, fps = 20 обеспечит полсекунды проезда без метки
current_freq = 0
previous_freq = 0



# Положи кроко С МЕТКОЙ под камеру. Освещение должно быть включёно. Кроко не должен двигаться. Если что просто положи метку на песок.
# В окне с видео мышкой выдели кусочек метки. Важно не вылезать за пределы метки.
# В гистограммах справа нужно определить Мин и Макс. Они будут болтаться немного, поэтому расширь немного диапазон.
# Подкорректируй данные тут (65, 90, 20, 60, -40, -10) в такой последовательности L Min, L Max, A Min, A Max, B Min, B Max.
# !!!!!!!! ЯРКОСТЬ И ЦВЕТ МЕТКИ               !!!!! (L Min, L Max, A Min, A Max, B Min, B Max)
thresholds = [(65, 90, 20, 60, -40, -10),(90, 100, -15, 15, -15, 15)]  # Яркостные и цветовые диапазоны
threshold_index = 0  # Если будет несколько диапазонов, нужно указать индекс (начинается с 0). НЕ ТРОГАТЬ!
pixels_threshold = 30  # Уменьши немного если метка слишком мелкая, например поставь 20



# Настройки оптического сенсора
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)  # для 320x240
sensor.skip_frames(time=1000)  # Ждём 2 секунды для теста забора изображений с сенсора
sensor.set_auto_gain(False, gain_db=-12) # False для точного поиска цвета, иначе поедет яркость
print('Camera Gain is {}'.format(sensor.get_gain_db()))
sensor.set_auto_exposure(False)
sensor.set_auto_whitebal(False) # False  для отключения автобаланса белого, иначе цвета будут плавать при каждом запуске

clock = time.clock()

# Only blobs that with more pixels than "pixel_threshold" and more area than "area_threshold" are
# returned by "find_blobs" below. Change "pixels_threshold" and "area_threshold" if you change the
# camera resolution. "merge=True" merges all overlapping blobs in the image.

while(True):
    clock.tick()
    img = sensor.snapshot()
    roi = (2, 30, 316, 195)  # Прямоугольник, в котором ищется метка (x, y, w, h)

    blobs = img.find_blobs([thresholds[threshold_index]], pixels_threshold=pixels_threshold, merge=True, roi=roi)  # Ищем блобы на кадре

    # Нам нужна задержка в N кадров (fps), чтобы двигатель не дёргался при потере изображения. Задержка вычисляется по счётчику, если объект не найден или найден
    if len(blobs) == 0:  # Нет метки в кадре
        if pause < fps:
            pause += 1
    else:
        if pause > 0:
            pause -= 4

    # N кадров без объекта = остановить генератор импульсов и снять ток с двигателя (чтобы не грелся)
    if pause == fps:
        motor.stop()


    for blob in blobs:

        img.draw_rectangle(blob.rect())
        img.draw_cross(blob.cx(), blob.cy())
        # Note - the blob rotation is unique to 0-180 only.
        #img.draw_keypoints([(blob.cx(), blob.cy(), int(math.degrees(blob.rotation())))], size=10)

        x = blob.cx()
        delta = x - 160

        # Получаем частоту
        current_freq = frequency_steps(delta)
        final_freq = intermediate_freq(current_freq, previous_freq)
        previous_freq = final_freq
        print('prev={}, cur={}, final={}'.format(previous_freq, current_freq, final_freq))


        # Отклонение больше границы вправо?
        if delta > border:
            motor.right()
            right = False
            if final_freq != current_freq:
                tim = pyb.Timer(2, freq=final_freq)
                tim.channel(3, mode=pyb.Timer.PWM, pin=pyb.Pin(PWM_pin), pulse_width_percent=5)
                motor.run()
        elif delta < -border:
            motor.left()
            right = True
            if final_freq != current_freq:
                tim = pyb.Timer(2, freq=final_freq)
                tim.channel(3, mode=pyb.Timer.PWM, pin=pyb.Pin(PWM_pin), pulse_width_percent=5)
                motor.run()
        else:
            motor.stop()

        # pyb.delay(100) # задержка


    # print(clock.fps())
