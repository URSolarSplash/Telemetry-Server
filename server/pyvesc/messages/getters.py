from pyvesc.messages.base import VESCMessage

class GetValues(metaclass=VESCMessage):
    """ Gets internal sensor data
    """
    id = 4

    fields = [
                ('temp_fet', 'h', 10),
                ('temp_motor', 'h', 10),
                ('avg_motor_current', 'i', 100),
                ('avg_input_current', 'i', 100),
                ('avg_id', 'i', 100),
                ('avg_iq', 'i', 100),
                ('duty_cycle_now', 'h', 1000),
                ('rpm', 'i', 1),
                ('v_in', 'h', 10),
                ('amp_hours', 'i', 10000),
                ('amp_hours_charged', 'i', 10000),
                ('watt_hours', 'i', 10000),
                ('watt_hours_charged', 'i', 10000),
                ('tachometer', 'i', 1),
                ('tachometer_abs', 'i', 1),
                ('mc_fault_code', 'c'),
                ('pid_pos_now', 'i', 1000000),
                ('app_controller_id', 'c')
        ]

    def __str__(self):
        return "values:  v_in {} duty_cycle_now {} avg_motor_current {}".format(self.v_in, self.duty_cycle_now, self.avg_motor_current)


class GetRotorPosition(metaclass=VESCMessage):
    """ Gets rotor position data

    Must be set to DISP_POS_MODE_ENCODER or DISP_POS_MODE_PID_POS (Mode 3 or
    Mode 4). This is set by SetRotorPositionMode (id=21).
    """
    id = 21

    fields = [
            ('rotor_pos', 'i', 100000)
    ]
