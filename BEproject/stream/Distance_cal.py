from gpiozero import AngularServo

class ServoController:
    def __init__(self):
        self.servo = AngularServo(14, min_angle=0, max_angle=90, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000)

    def set_angle(self,angle):
        self.servo.angle=angle
