#include <openmvrpc.h>
#include <Stepper.h>

#define STEPS 600

Stepper stepper(STEPS, 6, 3);
Stepper sndStepper(STEPS, 5, 2);

openmv::rpc_scratch_buffer<256> scratch_buffer;

// * slave_addr - I2C address.
// * rate - I2C Bus Clock Frequency.
//
// NOTE: Master and slave addresses must match. Connect master scl to slave scl and master sda
//       to slave sda. You must use external pull ups. Finally, both devices must share a ground.
//
openmv::rpc_i2c_master interface(0x12, 100000);

void setup() {
  // put your setup code here, to run once:
  interface.begin();
  Serial.begin(115200);
  stepper.setSpeed(40);
  sndStepper.setSpeed(20);
}

bool exe_person_detection()
{
    char buff[32 + 1] = {}; // null terminator
    if (interface.call_no_args(F("person_detection"), buff, sizeof(buff) - 1)) {
        Serial.println(buff);
    }
    return buff;
}

bool exe_qrcode_detection()
{
    char buff[128 + 1] = {}; // null terminator
    if (interface.call_no_args(F("qrcode_detection"), buff, sizeof(buff) - 1)) {
        Serial.println(buff);
        return true;
    }
    return false;
}

int val = 200;

void loop() {
  // put your main code here, to run repeatedly:
  //exe_qrcode_detection();
  //exe_person_detection();
  delay(3000);
  
  while (true) {
    stepper.step(val);
    stepper.step(-val);

    sndStepper.step(val);
    sndStepper.step(-val);

    if (exe_qrcode_detection()) {
      break;
    }
  }
}
