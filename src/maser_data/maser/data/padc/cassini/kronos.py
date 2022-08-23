# -*- coding: utf-8 -*-
import datetime


def freq_abc(nfilt):
    if nfilt == 8:
        return [
            3.9548,
            4.7729,
            5.7601,
            6.9516,
            8.3895,
            10.1248,
            12.2191,
            14.7465,
            17.7968,
            21.4779,
            25.9205,
            31.2821,
            37.7526,
            45.5616,
            54.9858,
            66.3593,
            80.0854,
            96.6507,
            116.6424,
            140.7693,
            169.8868,
            205.0270,
            247.4359,
            298.6168,
        ]
    elif nfilt == 16:
        return [
            3.7732,
            4.1452,
            4.5537,
            5.0026,
            5.4956,
            6.0373,
            6.6324,
            7.2861,
            8.0043,
            8.7932,
            9.6599,
            10.6120,
            11.6580,
            12.8071,
            14.0694,
            15.4562,
            16.9796,
            18.6532,
            20.4918,
            22.5115,
            24.7304,
            27.1679,
            29.8458,
            32.7875,
            36.0192,
            39.5694,
            43.4696,
            47.7542,
            52.4611,
            57.6319,
            63.3124,
            69.5528,
            76.4083,
            83.9395,
            92.2130,
            101.3019,
            111.2868,
            122.2558,
            134.3059,
            147.5438,
            162.0864,
            178.0625,
            195.6132,
            214.8939,
            236.0749,
            259.3436,
            284.9058,
            312.9876,
        ]
    elif nfilt == 32:
        return [
            3.6856,
            3.8630,
            4.0489,
            4.2437,
            4.4480,
            4.6620,
            4.8864,
            5.1215,
            5.3680,
            5.6263,
            5.8971,
            6.1809,
            6.4783,
            6.7901,
            7.1169,
            7.4594,
            7.8184,
            8.1946,
            8.5890,
            9.0023,
            9.4355,
            9.8896,
            10.3656,
            10.8644,
            11.3872,
            11.9352,
            12.5096,
            13.1116,
            13.7426,
            14.4040,
            15.0972,
            15.8237,
            16.5852,
            17.3834,
            18.2200,
            19.0968,
            20.0158,
            20.9791,
            21.9887,
            23.0469,
            24.1560,
            25.3185,
            26.5369,
            27.8140,
            29.1525,
            30.5555,
            32.0259,
            33.5672,
            35.1826,
            36.8757,
            38.6504,
            40.5104,
            42.4599,
            44.5033,
            46.6450,
            48.8898,
            51.2426,
            53.7086,
            56.2933,
            59.0024,
            61.8418,
            64.8179,
            67.9373,
            71.2067,
            74.6335,
            78.2252,
            81.9898,
            85.9355,
            90.0711,
            94.4057,
            98.9490,
            103.7109,
            108.7019,
            113.9331,
            119.4161,
            125.1629,
            131.1864,
            137.4996,
            144.1167,
            151.0523,
            158.3216,
            165.9408,
            173.9266,
            182.2967,
            191.0697,
            200.2648,
            209.9025,
            220.0039,
            230.5915,
            241.6886,
            253.3198,
            265.5107,
            278.2883,
            291.6808,
            305.7178,
            320.4303,
        ]


def fi_freq(fi):

    fi_b = fi // 10000000
    fi_ccc = (fi % 10000000) // 10000
    fi_ff = (fi % 10000) // 100
    fi_nn = fi % 100

    if fi_b <= 2:
        return freq_abc(fi_ff)[fi_b * fi_ff + fi_nn]
    else:
        return (fi_ccc + (2 * fi_nn - fi_ff + 1) / (2 * fi_ff)) * 25


def ti_datetime(ti, c):
    yy = int(ti // 100000000) + 1996
    dd = int(ti % 100000000) // 100000
    ss = float(ti % 100000)
    ms = int(c) * 10000

    return datetime.datetime(yy, 1, 1) + datetime.timedelta(
        days=(dd - 1), seconds=ss, microseconds=ms
    )
