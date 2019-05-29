from pyvesc.messages.base import VESCMessage

class GetValues(metaclass=VESCMessage):
    """ Gets internal sensor data
        valid for use with vesc firmware 3.57
    """
    id = 4
    fields = [
        ('temp_fet_filtered','h',10),
        ('temp_motor_filtered','h',10),
        ('avg_motor_current','i',100),
        ('avg_input_current','i',100),
        ('foc_avg_id','i',100),
        ('foc_avg_iq','i',100),
        ('duty_cycle','h',100),
        ('rpm','i',1),
        ('v_in','h',10),
        ('amp_hours','i',10000),
        ('amp_hours_charged','i',10000),
        ('watt_hours','i',10000),
        ('watt_hours_charged','i',10000),
        ('tachometer','i',1),
        ('tachometer_abs','i',1),
        ('mc_fault_code','c'),
        ('pid_pos_now','i',1000000),
        ('app_config','c'),
        ('temp_mos1','h',10),
        ('temp_mos2','h',10),
        ('temp_mos3','h',10)
    ]

class GetRotorPosition(metaclass=VESCMessage):
    """ Gets rotor position data
    
    Must be set to DISP_POS_MODE_ENCODER or DISP_POS_MODE_PID_POS (Mode 3 or 
    Mode 4). This is set by SetRotorPositionMode (id=21).
    """
    id = 21

    fields = [
            ('rotor_pos', 'i', 100000)
    ]
