use anyhow::{anyhow, Context};
use serde::Serialize;
use tokio::time::timeout;
use tokio::time::delay_for;

use std::default::Default;
use std::sync::{Arc,Mutex};
use std::time::{Duration, Instant};

use crate::error::Result;
use crate::eventbroker::{EventBroker, timestamp_now};
use crate::location::{Location, Rectangle, Direction};
use crate::{board::Board, devices};
use crate::settings::Settings;
use crate::devices::driver::CapacitanceEvent;
use crate::protobuf:: {
    {PurpleDropEvent, ElectrodeState},
    purple_drop_event::Msg,
};

use log::*;

#[derive(Clone, Debug, Default, Serialize)]
pub struct MoveDropResult {
    success: bool,
    closed_loop: bool,
    closed_loop_result: Option<MoveDropClosedLoopResult>,
}

#[derive(Clone, Debug, Default, Serialize)]
pub struct MoveDropClosedLoopResult {
    pre_capacitance: f32,
    post_capacitance: f32,
    time_series: Vec<f32>,
    capacitance_series: Vec<f32>,
}

#[cfg(target_arch = "arm")]
pub struct BackgroundTempReader {
    //sensors: Vec<devices::max31865::Max31865>,
    latest: Arc<Mutex<Vec<f32>>>,
}

#[cfg(target_arch = "arm")]
impl BackgroundTempReader {
    pub fn new(sensors: Vec<devices::max31865::Max31865>) -> BackgroundTempReader{
        let latest = Arc::new(Mutex::new(vec![0.0; sensors.len()]));
        let ret = BackgroundTempReader{latest: latest.clone()};
        Self::start(sensors, latest.clone());
        ret
    }
    pub fn start(mut sensors: Vec<devices::max31865::Max31865>, latest: Arc<Mutex<Vec<f32>>>) {
        // Create a list of Interval streams, one per sensor, these will yield () periodically
        // at the rate of each sensor.
        let mut streams = Vec::new();
        for s in &sensors {
            streams.push(tokio::time::interval(Duration::from_secs_f32(1.0 / s.read_frequency)));
        }
        if streams.len() == 0 {
            return;
        }
        tokio::spawn(async move {
            loop {
                // Convert the streams to a list of futures for select_all
                let futures = streams.iter_mut().map(|s| Box::pin(s.tick()));
                let (_res, idx, _remaining_futures) = futures::future::select_all(futures).await;
                {
                    //let arc = latest.clone();
                    let mut locked = latest.lock().expect("Failed to lock BackgroundTempReader output");
                    match sensors[idx].read_temperature() {
                        Ok(temp) => locked[idx] = temp,
                        Err(e) => error!("Error reading from MAX31865: {:?}", e),
                    };
                }
            }
        });
    }
    pub fn get_temperatures(&mut self) -> Result<Vec<f32>> {
        let latest = self.latest.clone().lock().unwrap().clone();
        Ok(latest)
    }
}

#[cfg(not(target_arch = "arm"))]
pub struct PurpleDrop {
    pub board: Board,
    pub event_broker: Mutex<EventBroker>,
}

#[cfg(target_arch = "arm")]
pub struct PurpleDrop {
    pub board: Board,
    pub event_broker: Mutex<EventBroker>,
    pub driver: Box<dyn devices::driver::Driver>,
    pub mcp4725: Option<devices::mcp4725::Mcp4725>,
    pub pca9685: Option<devices::pca9685::Pca9685>,
    pub max31865: BackgroundTempReader,
}

impl PurpleDrop {
    pub fn new(settings: Settings, event_broker: EventBroker) -> Result<PurpleDrop> {
        trace!("Initializing purpledrop...");

        let driver: Box<dyn devices::driver::Driver>;
        let max31865;
        #[cfg(target_arch="arm")]
        {
            if settings.pd_driver.is_some() {
                let pd_driver_settings = settings.pd_driver.unwrap();
                info!("Using pd-driver on port {}", pd_driver_settings.port);
                driver = Box::new(pd_driver_settings.make(event_broker.clone())?);
            } else if cfg!(target_arch = "arm") && settings.hv507.is_some() {
                info!("Using HV507 driver");
                driver = Box::new(settings.hv507.unwrap().make()?);
            } else {
                panic!("Must provide either an hv507 or pddriver config section");
            }

            max31865 = match settings.max31865.map(|s| s.iter().map(|t| t.make()).collect()).transpose()? {
                Some(devices) => BackgroundTempReader::new(devices),
                None => BackgroundTempReader::new(Vec::new()),
            };
        }

        let pd = PurpleDrop {
            board: settings.board.clone(),
            event_broker: Mutex::new(event_broker.clone()),
            #[cfg(target_arch = "arm")]
            driver: driver,
            #[cfg(target_arch = "arm")]
            mcp4725: settings.mcp4725.map(|s| s.make()).transpose()?,
            #[cfg(target_arch = "arm")]
            pca9685: settings.pca9685.map(|s| s.make()).transpose()?,
            #[cfg(target_arch = "arm")]
            max31865: max31865,
        };

        trace!("Initialized purpledrop!");

        Ok(pd)
    }

    /// Returns the number of electrodes supported by purple drop hardware
    pub fn n_pins() -> usize {
        128
    }

    /// Set the electrode drive frequency
    ///
    /// # Arguments
    ///
    /// * `f` - Floating point frequency in Hz
    pub fn set_frequency(&mut self, f: f64) -> Result<()> {
        #[cfg(target_arch = "arm")]
        self.driver.set_frequency(f)?;
        Ok(())
    }

    pub fn bulk_capacitance(&self) -> Result<Vec<f32>> {
        #[cfg(target_arch = "arm")]
        {
        if self.driver.has_capacitance_feedback() {
            return Ok(self.driver.bulk_capacitance());
        }
        }
        Err(anyhow!("No capacitance measurement available"))
    }

    // pub fn heat(
    //     &mut self,
    //     _heater: &Peripheral,
    //     _target_temperature: f64,
    //     _duration: Duration,
    // ) -> Result<()> {
    //     unimplemented!()
    //     // // FIXME: for now, this simply blocks

    //     // let pwm_channel = if let Peripheral::Heater { pwm_channel, .. } = heater {
    //     //     *pwm_channel
    //     // } else {
    //     //     panic!("Peripheral wasn't a heater!: {:#?}", heater)
    //     // };

    //     // let mut pid = PidController::default();
    //     // pid.p_gain = 1.0;
    //     // pid.i_gain = 1.0;
    //     // pid.d_gain = 1.0;

    //     // use std::env;

    //     // pid.p_gain = env::var("PID_P").unwrap_or("1.0".into()).parse().unwrap();
    //     // pid.i_gain = env::var("PID_I").unwrap_or("1.0".into()).parse().unwrap();
    //     // pid.d_gain = env::var("PID_D").unwrap_or("1.0".into()).parse().unwrap();

    //     // pid.i_min = 0.0;
    //     // pid.i_max = pca9685::DUTY_CYCLE_MAX as f64;

    //     // pid.out_min = 0.0;
    //     // pid.out_max = pca9685::DUTY_CYCLE_MAX as f64;

    //     // pid.target = target_temperature;

    //     // let epsilon = 2.0; // degrees C
    //     // let extra_delay = Duration::from_millis(20);

    //     // let mut timer = Timer::new();
    //     // let mut in_range_start: Option<Instant> = None;

    //     // for iteration in 0.. {
    //     //     // stop if we've been in the desired temperature range for long enough
    //     //     if in_range_start
    //     //         .map(|t| t.elapsed() > duration)
    //     //         .unwrap_or(false)
    //     //     {
    //     //         break;
    //     //     }

    //     //     // FIXME HACK the mcp thing is bad here
    //     //     self.mcp4725.write(0).unwrap();
    //     //     thread::sleep(Duration::from_millis(30));
    //     //     let measured = self.max31865.read_one_temperature()? as f64;
    //     //     self.mcp4725.write(1600).unwrap();

    //     //     let dt = timer.lap();
    //     //     let mut duty_cycle = pid.update(measured, &dt);

    //     //     debug!(
    //     //         "Heating to {}*C... iteration: {}, measured: {}*C, duty_cycle: {}",
    //     //         target_temperature, iteration, measured, duty_cycle
    //     //     );

    //     //     if measured - target_temperature > epsilon {
    //     //         self.pca9685.set_duty_cycle(pwm_channel, 0)?;
    //     //         warn!(
    //     //             "We overshot the target temperature. Wanted {}, got {}",
    //     //             target_temperature, measured
    //     //         );
    //     //         duty_cycle = 0.0;
    //     //     }

    //     //     if (target_temperature - measured).abs() < epsilon && in_range_start.is_none() {
    //     //         in_range_start = Some(Instant::now())
    //     //     }

    //     //     assert!(0.0 <= duty_cycle);
    //     //     assert!(duty_cycle <= pca9685::DUTY_CYCLE_MAX as f64);
    //     //     self.pca9685
    //     //         .set_duty_cycle(pwm_channel, duty_cycle as u16)?;

    //     //     thread::sleep(extra_delay);
    //     // }

    //     // self.pca9685.set_duty_cycle(pwm_channel, 0)?;

    //     // Ok(())
    // }

    // pub fn get_temperature(&mut self, _temp_sensor: Peripheral) -> Result<f32> {
    //     unimplemented!()
    //     // if let Peripheral::Heater { spi_channel, .. } = temp_sensor {
    //     //     // right now we can only work on the one channel
    //     //     assert_eq!(spi_channel, 0);
    //     //     self.max31865.read_temperature()
    //     // } else {
    //     //     panic!("Not a temperature sensor!: {:#?}")
    //     // }
    // }
    pub fn output_pins(&mut self, pins: &[bool]) {
        let n = Self::n_pins();
        assert_eq!(pins.len(), n);

        debug!("Setting pins: {:?}", pins);

        #[cfg(target_arch = "arm")]
        {
            self.driver.clear_pins();
            for (i, on) in pins.iter().enumerate() {
                if *on {
                    self.driver.set_pin_hi(i);
                }
            }

            self.driver.shift_and_latch();
        }

        let msg = ElectrodeState{timestamp: Some(timestamp_now()), electrodes: pins.to_vec()};
        let event = PurpleDropEvent{msg: Some(Msg::ElectrodeState(msg))};
        let mut event_broker = self.event_broker.lock().unwrap();
        event_broker.send(event);
    }

    pub fn output_locations(&mut self, locations: &[Location]) {
        let n = self.board.layout.n_pins();
        let mut pins = vec![false; n];

        for loc in locations {
            let pin_num = self
                .board
                .layout
                .get_pin(*loc)
                .unwrap_or_else(|| panic!("No pin at location: {}", loc));
            pins[pin_num] = true;
        }

        self.output_pins(&pins);
    }

    pub fn output_rects(&mut self, rects: &[Rectangle]) {
        let locs: Vec<_> = rects.iter().flat_map(|r| r.clone().locations()).collect();
        self.output_locations(&locs)
    }

    pub async fn move_drop(&mut self, start: Location, size: Location, dir: Direction) -> Result<MoveDropResult> {

        async fn wait_for_ack(rx: &mut devices::driver::CapacitanceReceiver) -> Result<()> {
            loop {
                match rx.recv().await? {
                    CapacitanceEvent::Ack => return Ok(()),
                    _ => warn!("Got unexpected event"),
                }
            }
        }
        async fn wait_for_measurement(rx: &mut devices::driver::CapacitanceReceiver) -> Result<f32> {
            loop {
                match rx.recv().await? {
                    CapacitanceEvent::Measurement(x) => return Ok(x),
                    _ => warn!("Got unexpected event"),
                }
            }
        }
        async fn wait_for_capacitance(rx: &mut devices::driver::CapacitanceReceiver, wait_time: Duration, threshold: f32, trailing_samples: usize) -> (Vec<f32>, Vec<f32>) {
            let start = Instant::now();
            let mut t = 0.0;
            let mut timeseries = Vec::new();
            let mut capseries = Vec::new();
            let mut trailing_count:usize  = 0;
            loop {
                let runtime = start.elapsed();
                if runtime > wait_time {
                    break;
                }
                match timeout(Duration::from_millis(100), rx.recv()).await.unwrap().unwrap() {
                    CapacitanceEvent::Measurement(x) => {
                        // For now, just assume the samplers are periodic at 2ms and create a time vector
                        // This conveys little information, but it's a stand-in for a potential different
                        // strategy in the future
                        timeseries.push(t);
                        t += 2e-3;
                        capseries.push(x);
                        if x > threshold {
                            if trailing_count >= trailing_samples {
                                break;
                            }
                            trailing_count += 1;
                        }
                    },
                    _ => (),
                }
            }

            (timeseries, capseries)
        }


        #[cfg(target_arch = "arm")]
        {
            let initial_rect = Rectangle{location: start, dimensions: size};
            let final_rect = Rectangle{location: start.move_one(dir), dimensions: size};

            if self.driver.has_capacitance_feedback() {
                // Perform closed loop move
                let mut events = self.driver.capacitance_channel().unwrap();


                // Enable electrodes for start position
                self.output_rects(&[initial_rect]);

                // Wait for ack
                match timeout(Duration::from_millis(200), wait_for_ack(&mut events)).await {
                    Ok(_) => info!("GOT ACK"),
                    Err(e) => info!("ERR WAITING ON ACK: {:?}", e),
                };

                // Wait for one active measurement
                let pre_capacitance = timeout(Duration::from_millis(200), wait_for_measurement(&mut events)).await.context("Failed waiting for initial capacitance measurement")??;

                self.output_rects(&[final_rect]);
                // Wait for ack
                match timeout(Duration::from_millis(200), wait_for_ack(&mut events)).await {
                    Ok(_) => info!("GOT ACK 2"),
                    Err(e) => info!("ERR WAITING ON ACK: {:?}", e),
                };

                let (time_series, capacitance_series) = wait_for_capacitance(&mut events, Duration::from_millis(3000), 0.8 * pre_capacitance, 500)
                    .await;

                let mut post_capacitance: f32 = 0.0;
                if capacitance_series.len() > 0 {
                    post_capacitance = capacitance_series[capacitance_series.len() - 1];
                }

                let success = post_capacitance > 0.8 * pre_capacitance;

                Ok(MoveDropResult{
                    success,
                    closed_loop: true,
                    closed_loop_result: Some(MoveDropClosedLoopResult{pre_capacitance, post_capacitance, time_series, capacitance_series}),
                })

            } else {
                // TODO: This should be adjustable (need config api)
                const MOVE_TIME: f32 = 1.0;

                self.output_rects(&[final_rect]);

                delay_for(Duration::from_secs_f32(MOVE_TIME)).await;

                Ok(MoveDropResult{
                    success: true,
                    closed_loop: false,
                    closed_loop_result: None,
                })
            }
        }

        #[cfg(not(target_arch = "arm"))]
        Ok(MoveDropResult::default())
    }

    /// Set pwm output channel on the PCA9685 to a particular duty cycle
    pub fn set_pwm_duty_cycle(&mut self, chan: u8, duty_cycle: f32) -> Result<()> {
        #[cfg(target_arch="arm")]
        {
            if self.pca9685.is_some() {
                self.pca9685.as_mut().expect("no PCA").set_duty_cycle(chan, (duty_cycle * 4095.) as u16)?;
            } else {
                return Err(anyhow!("No pca9685 is defined"));
            }
        }
        Ok(())
    }

    pub fn temperatures(&mut self) -> Result<Vec<f32>> {
        #[cfg(target_arch="arm")]
        return Ok(self.max31865.get_temperatures().expect("Failed to unwrap max31865 temps"));

        #[cfg(not(target_arch="arm"))]
        return Ok(vec![]);
    }


    // pub fn input(&mut self, _input_port: &Peripheral, _volume: f64) -> Result<()> {
    //     unimplemented!()
    //     //     let pwm_channel = if let Peripheral::Input { pwm_channel, .. } = input_port {
    //     //         *pwm_channel
    //     //     } else {
    //     //         panic!("Peripheral wasn't an input port!: {:#?}", input_port)
    //     //     };

    //     //     let pump_duty_cycle = pca9685::DUTY_CYCLE_MAX / 2;

    //     //     let pump_duration = {
    //     //         // n.b. max flow rate is .45 ml/min +/- 15% at 20 C, or 7.5 ul/s
    //     //         let ul_per_second = 7.0;
    //     //         let ul_per_volume = 1.0;
    //     //         let seconds = volume * ul_per_volume / ul_per_second;
    //     //         seconds_duration(seconds)
    //     //     };

    //     //     self.pca9685.set_duty_cycle(pwm_channel, pump_duty_cycle)?;
    //     //     thread::sleep(pump_duration);
    //     //     self.pca9685.set_duty_cycle(pwm_channel, 0)?;
    //     //     Ok(())
    // }

    // pub fn output(&mut self, _output_port: &Peripheral, _volume: f64) -> Result<()> {
    //     unimplemented!()
    //     //     let pwm_channel = if let Peripheral::Output { pwm_channel, .. } = output_port {
    //     //         *pwm_channel
    //     //     } else {
    //     //         panic!("Peripheral wasn't an output port!: {:#?}", output_port)
    //     //     };

    //     //     let pump_duty_cycle = pca9685::DUTY_CYCLE_MAX / 2;

    //     //     let pump_duration = {
    //     //         // n.b. max flow rate is .45 ml/min +/- 15% at 20 C, or 7.5 ul/s
    //     //         let ul_per_second = 4.0;
    //     //         let ul_per_volume = 4.0;
    //     //         let seconds = volume * ul_per_volume / ul_per_second;
    //     //         seconds_duration(seconds)
    //     //     };

    //     //     self.pca9685.set_duty_cycle(pwm_channel, pump_duty_cycle)?;
    //     //     thread::sleep(pump_duration);
    //     //     self.pca9685.set_duty_cycle(pwm_channel, 0)?;
    //     //     Ok(())
    // }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn make_purpledrop_settings() {
        let _ = Settings::from_file("config/default.toml").unwrap();
    }
}
