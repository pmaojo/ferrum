use rppal::gpio::Gpio;

pub fn blink_gpio() -> Gpio {
    // ⛳ AI_FILL[iot_gpio] --context=iot:blink
    Gpio::new().unwrap()
}
